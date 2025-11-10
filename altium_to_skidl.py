#!/usr/bin/env python3
"""
Altium to SKiDL Converter

This module converts Altium SchDoc files to SKiDL Python code.
The workflow:
1. Parse Altium file using altium_parser
2. Analyze schematic (components, nets, connections)
3. Generate SKiDL Python code
4. Execute SKiDL to generate KiCad files
"""

from typing import List, Dict, Set, Tuple, Optional
from dataclasses import dataclass, field
from altium_parser import AltiumParser
from altium_objects import (
    Component, Pin, Wire, NetLabel, PowerPort, Junction,
    PinElectrical, SchDoc, AltiumObject
)
import os
import math


@dataclass
class NetInfo:
    """Represents a net with its connections"""
    name: str
    pins: List[Tuple[str, str]] = field(default_factory=list)  # (component_designator, pin_name)
    is_power: bool = False
    is_ground: bool = False


@dataclass
class ComponentInfo:
    """Analyzed component information for SKiDL generation"""
    designator: str
    library_reference: str
    value: str = ""
    footprint: str = ""
    part_number: str = ""
    description: str = ""
    x: float = 0.0
    y: float = 0.0
    pins: Dict[str, str] = field(default_factory=dict)  # pin_number -> pin_name


class SchematicAnalyzer:
    """Analyzes parsed Altium schematic data"""

    def __init__(self, schdoc: SchDoc):
        self.schdoc = schdoc
        self.components: Dict[str, ComponentInfo] = {}
        self.nets: Dict[str, NetInfo] = {}

    def analyze(self) -> Tuple[Dict[str, ComponentInfo], Dict[str, NetInfo]]:
        """Analyze the schematic and extract component and net information"""
        self._analyze_components()
        self._analyze_nets()
        return self.components, self.nets

    def _analyze_components(self):
        """Extract component information"""
        for comp in self.schdoc.get_components():
            if not comp.designator:
                continue

            comp_info = ComponentInfo(
                designator=comp.designator,
                library_reference=comp.library_reference or "UNKNOWN",
                x=comp.location_x / 100.0,  # Convert from 1/100 inch to inches
                y=comp.location_y / 100.0
            )

            # Extract value and other parameters from component children
            for child in comp.children:
                if hasattr(child, 'name') and hasattr(child, 'text'):
                    name = getattr(child, 'name', '').upper()
                    text = getattr(child, 'text', '')

                    if name == 'VALUE' or name == 'COMMENT':
                        comp_info.value = text
                    elif name == 'FOOTPRINT':
                        comp_info.footprint = text
                    elif name == 'PART NUMBER' or name == 'PARTNUMBER':
                        comp_info.part_number = text
                    elif name == 'DESCRIPTION':
                        comp_info.description = text

            # Extract pin information
            for child in comp.children:
                if isinstance(child, Pin):
                    pin_num = child.designator or ""
                    pin_name = child.name or pin_num
                    comp_info.pins[pin_num] = pin_name

            self.components[comp.designator] = comp_info

    def _analyze_nets(self):
        """Extract net information by tracing connections"""
        # Collect all devices that can be part of nets
        devices = []

        # Add wires
        for wire in self.schdoc.get_wires():
            devices.append({
                'type': 'wire',
                'obj': wire,
                'coords': [(x, y) for x, y in wire.points]
            })

        # Add pins with calculated coordinates
        for comp in self.schdoc.get_components():
            if not comp.designator:
                continue

            for child in comp.children:
                if isinstance(child, Pin):
                    # Calculate pin connection point considering rotation
                    # Pin conglomerate bits 0-1 encode rotation
                    rotation_bits = child.pin_conglomerate & 0x03
                    rotation_degrees = rotation_bits * 90

                    # Pin length is in bits 2-9 of conglomerate (in units of 1/10000 inch)
                    pin_length = ((child.pin_conglomerate >> 2) & 0xFF) * 10

                    # Calculate connection point
                    angle_rad = math.radians(rotation_degrees)
                    conn_x = comp.location_x + child.location_x + int(math.cos(angle_rad) * pin_length)
                    conn_y = comp.location_y + child.location_y + int(math.sin(angle_rad) * pin_length)

                    devices.append({
                        'type': 'pin',
                        'obj': child,
                        'component': comp,
                        'designator': comp.designator,
                        'pin_num': child.designator or "",
                        'coords': [(conn_x, conn_y)]
                    })

        # Add net labels
        for label in self.schdoc.get_net_labels():
            devices.append({
                'type': 'label',
                'obj': label,
                'name': label.text,
                'coords': [(label.location_x, label.location_y)]
            })

        # Add power ports
        for port in self.schdoc.get_power_ports():
            devices.append({
                'type': 'power',
                'obj': port,
                'name': port.text,
                'coords': [(port.location_x, port.location_y)]
            })

        # Group connected devices into nets
        nets_list = []
        processed = set()

        for device in devices:
            device_id = id(device['obj'])
            if device_id in processed:
                continue

            # Find all connected devices
            connected = self._find_connected_devices(device, devices, processed)
            if connected:
                nets_list.append(connected)

        # Assign net names and create NetInfo objects
        net_counter = 1
        for net_devices in nets_list:
            # Try to find a name from labels or power ports
            net_name = None
            for dev in net_devices:
                if dev['type'] in ['label', 'power'] and 'name' in dev:
                    net_name = dev['name']
                    break

            # If no name found, generate one
            if not net_name:
                # Try to get name from first pin's component
                pin_dev = next((d for d in net_devices if d['type'] == 'pin'), None)
                if pin_dev:
                    net_name = f"Net{pin_dev['designator']}_{pin_dev['pin_num']}"
                else:
                    net_name = f"Net{net_counter}"
                    net_counter += 1

            # Determine if power or ground
            is_power = False
            is_ground = False
            net_name_upper = net_name.upper()

            if any(g in net_name_upper for g in ['GND', 'GROUND', 'VSS']):
                is_ground = True
            elif any(p in net_name_upper for p in ['VCC', 'VDD', 'VEE', 'POWER', '+5V', '+3.3V', '+12V']):
                is_power = True

            # Create NetInfo
            net_info = NetInfo(
                name=net_name,
                is_power=is_power,
                is_ground=is_ground
            )

            # Add pin connections
            for dev in net_devices:
                if dev['type'] == 'pin':
                    net_info.pins.append((dev['designator'], dev['pin_num']))

            if net_info.pins:  # Only add nets with actual pin connections
                self.nets[net_name] = net_info

    def _find_connected_devices(self, start_device, all_devices, processed, threshold=50):
        """Recursively find all devices connected to start_device"""
        connected = [start_device]
        processed.add(id(start_device['obj']))
        to_check = [start_device]

        while to_check:
            current = to_check.pop(0)

            for device in all_devices:
                device_id = id(device['obj'])
                if device_id in processed:
                    continue

                # Check if devices are connected (coordinates are close)
                if self._devices_connected(current, device, threshold):
                    connected.append(device)
                    processed.add(device_id)
                    to_check.append(device)

        return connected

    def _devices_connected(self, dev1, dev2, threshold=50):
        """Check if two devices are electrically connected"""
        # Check if any coordinate pair is within threshold distance
        for x1, y1 in dev1['coords']:
            for x2, y2 in dev2['coords']:
                distance = math.sqrt((x1 - x2)**2 + (y1 - y2)**2)
                if distance <= threshold:
                    return True
        return False


class SKiDLCodeGenerator:
    """Generates SKiDL Python code from analyzed schematic data"""

    def __init__(self, components: Dict[str, ComponentInfo], nets: Dict[str, NetInfo]):
        self.components = components
        self.nets = nets
        self.net_objects: Set[str] = set()

    def generate(self, output_file: str = "schematic.py",
                 pcb_output: str = "output.kicad_pcb",
                 netlist_output: str = "output.net") -> str:
        """Generate SKiDL code"""

        code_lines = []

        # Header
        code_lines.extend(self._generate_header(pcb_output, netlist_output))
        code_lines.append("")

        # Define nets
        code_lines.extend(self._generate_nets())
        code_lines.append("")

        # Define components
        code_lines.extend(self._generate_components())
        code_lines.append("")

        # Make connections
        code_lines.extend(self._generate_connections())
        code_lines.append("")

        # Footer
        code_lines.extend(self._generate_footer())

        code = "\n".join(code_lines)

        # Write to file
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(code)

        return code

    def _generate_header(self, pcb_output: str, netlist_output: str) -> List[str]:
        """Generate SKiDL header"""
        return [
            '"""',
            'SKiDL Circuit - Generated from Altium SchDoc',
            'This file can be executed to generate KiCad files',
            '"""',
            '',
            'from skidl import *',
            '',
            '# Set the default tool to KiCad',
            'set_default_tool(KICAD8)',
            '',
            f'# Output file paths',
            f'PCB_OUTPUT = "{pcb_output}"',
            f'NETLIST_OUTPUT = "{netlist_output}"',
        ]

    def _generate_nets(self) -> List[str]:
        """Generate net definitions"""
        lines = ['# ========== Net Definitions ==========']

        # Create special nets first (power and ground)
        for net_name, net_info in sorted(self.nets.items()):
            if net_info.is_power or net_info.is_ground:
                var_name = self._sanitize_net_name(net_name)
                self.net_objects.add(var_name)
                lines.append(f'{var_name} = Net("{net_name}")')

        # Create other nets
        for net_name, net_info in sorted(self.nets.items()):
            if not (net_info.is_power or net_info.is_ground):
                var_name = self._sanitize_net_name(net_name)
                self.net_objects.add(var_name)
                lines.append(f'{var_name} = Net("{net_name}")')

        return lines

    def _generate_components(self) -> List[str]:
        """Generate component definitions"""
        lines = ['# ========== Component Definitions ==========']

        for designator, comp in sorted(self.components.items()):
            # Determine SKiDL part definition
            lib_ref = comp.library_reference
            value = comp.value or lib_ref
            footprint = comp.footprint or "Package_SO:SOIC-8_3.9x4.9mm_P1.27mm"

            # Try to map common Altium parts to SKiDL library
            part_def = self._get_skidl_part(lib_ref, value, comp)

            comment_parts = []
            if comp.value:
                comment_parts.append(f"Value: {comp.value}")
            if comp.footprint:
                comment_parts.append(f"Footprint: {comp.footprint}")

            comment = f"  # {', '.join(comment_parts)}" if comment_parts else ""

            lines.append(f'{designator} = Part("{part_def["lib"]}", "{part_def["name"]}", '
                        f'footprint="{footprint}", value="{value}", '
                        f'ref="{designator}"){comment}')

        return lines

    def _generate_connections(self) -> List[str]:
        """Generate net connections"""
        lines = ['# ========== Connections ==========']

        for net_name, net_info in sorted(self.nets.items()):
            if not net_info.pins:
                continue

            var_name = self._sanitize_net_name(net_name)
            lines.append(f'# Net: {net_name}')

            for designator, pin_num in net_info.pins:
                if designator in self.components:
                    # Use SKiDL pin connection syntax
                    lines.append(f'{var_name} += {designator}["{pin_num}"]')

            lines.append('')

        return lines

    def _generate_footer(self) -> List[str]:
        """Generate SKiDL footer with ERC and output generation"""
        return [
            '# ========== Generate Output Files ==========',
            'if __name__ == "__main__":',
            '    # Perform electrical rule check',
            '    ERC()',
            '    ',
            '    # Generate KiCad netlist',
            '    generate_netlist(file_=NETLIST_OUTPUT)',
            '    print(f"Generated netlist: {NETLIST_OUTPUT}")',
            '    ',
            '    # Generate KiCad PCB (requires pcbnew)',
            '    try:',
            '        generate_pcb(file_=PCB_OUTPUT)',
            '        print(f"Generated PCB: {PCB_OUTPUT}")',
            '    except Exception as e:',
            '        print(f"PCB generation failed: {e}")',
            '        print("You may need to install KiCad and ensure pcbnew is in PATH")',
        ]

    def _sanitize_net_name(self, net_name: str) -> str:
        """Convert net name to valid Python variable name"""
        # Replace invalid characters
        sanitized = net_name.replace('+', 'P').replace('-', 'N').replace('.', '_')
        sanitized = ''.join(c if c.isalnum() or c == '_' else '_' for c in sanitized)

        # Ensure it doesn't start with a number
        if sanitized and sanitized[0].isdigit():
            sanitized = 'NET_' + sanitized

        return sanitized or 'NET_UNNAMED'

    def _get_skidl_part(self, lib_ref: str, value: str, comp: ComponentInfo) -> Dict[str, str]:
        """Map Altium part to SKiDL library part"""
        lib_ref_upper = lib_ref.upper()

        # Common discrete components
        if lib_ref_upper.startswith('R'):
            return {"lib": "Device", "name": "R"}
        elif lib_ref_upper.startswith('C'):
            return {"lib": "Device", "name": "C"}
        elif lib_ref_upper.startswith('L'):
            return {"lib": "Device", "name": "L"}
        elif lib_ref_upper.startswith('D'):
            return {"lib": "Device", "name": "D"}
        elif lib_ref_upper.startswith('Q'):
            return {"lib": "Device", "name": "Q_NPN_BCE"}
        elif lib_ref_upper.startswith('U') or lib_ref_upper.startswith('IC'):
            # Try to identify specific ICs
            value_upper = value.upper()
            if 'LM358' in value_upper or 'LM358' in lib_ref_upper:
                return {"lib": "Amplifier_Operational", "name": "LM358"}
            elif '555' in value_upper or '555' in lib_ref_upper:
                return {"lib": "Timer", "name": "NE555"}
            elif 'OPAMP' in lib_ref_upper:
                return {"lib": "Amplifier_Operational", "name": "LM358"}
            else:
                # Generic IC
                return {"lib": "Device", "name": "C"}  # Placeholder

        # Default to a generic part
        return {"lib": "Device", "name": lib_ref}


class AltiumToSKiDLConverter:
    """Main converter class that orchestrates the conversion process"""

    def __init__(self, altium_file: str):
        self.altium_file = altium_file
        self.schdoc: Optional[SchDoc] = None
        self.components: Dict[str, ComponentInfo] = {}
        self.nets: Dict[str, NetInfo] = {}

    def parse_altium(self):
        """Step 1: Parse Altium file"""
        print(f"Parsing Altium file: {self.altium_file}")
        parser = AltiumParser()
        self.schdoc = parser.parse_file(self.altium_file)
        print(f"  - Found {len(self.schdoc.get_components())} components")
        print(f"  - Found {len(self.schdoc.get_wires())} wires")
        print(f"  - Found {len(self.schdoc.get_net_labels())} net labels")
        return self.schdoc

    def analyze_schematic(self):
        """Step 2: Analyze schematic data"""
        print("\nAnalyzing schematic...")
        analyzer = SchematicAnalyzer(self.schdoc)
        self.components, self.nets = analyzer.analyze()
        print(f"  - Analyzed {len(self.components)} components")
        print(f"  - Identified {len(self.nets)} nets")
        return self.components, self.nets

    def generate_skidl(self, output_file: str = "schematic.py",
                      pcb_output: str = "output.kicad_pcb",
                      netlist_output: str = "output.net") -> str:
        """Step 3: Generate SKiDL code"""
        print(f"\nGenerating SKiDL code: {output_file}")
        generator = SKiDLCodeGenerator(self.components, self.nets)
        code = generator.generate(output_file, pcb_output, netlist_output)
        print(f"  - SKiDL code written to {output_file}")
        return code

    def execute_skidl(self, skidl_file: str = "schematic.py"):
        """Step 4: Execute SKiDL to generate KiCad files"""
        print(f"\nExecuting SKiDL code: {skidl_file}")
        import subprocess
        result = subprocess.run(['python3', skidl_file],
                              capture_output=True, text=True)

        if result.returncode == 0:
            print("  - SKiDL execution successful")
            print(result.stdout)
        else:
            print("  - SKiDL execution failed")
            print(result.stderr)
            raise RuntimeError(f"SKiDL execution failed: {result.stderr}")

        return result

    def convert(self, skidl_output: str = "schematic.py",
                pcb_output: str = "output.kicad_pcb",
                netlist_output: str = "output.net",
                execute: bool = True) -> str:
        """
        Complete conversion pipeline

        Args:
            skidl_output: Output SKiDL Python file
            pcb_output: Output KiCad PCB file
            netlist_output: Output KiCad netlist file
            execute: Whether to execute the SKiDL code

        Returns:
            Generated SKiDL code
        """
        # Parse
        self.parse_altium()

        # Analyze
        self.analyze_schematic()

        # Generate SKiDL
        code = self.generate_skidl(skidl_output, pcb_output, netlist_output)

        # Execute SKiDL
        if execute:
            try:
                self.execute_skidl(skidl_output)
            except RuntimeError as e:
                print(f"\nWarning: {e}")
                print("SKiDL code was generated but execution failed.")
                print("You can manually install SKiDL and run the generated code.")

        return code

    def print_analysis_summary(self):
        """Print a summary of the analyzed schematic"""
        print("\n" + "="*60)
        print("SCHEMATIC ANALYSIS SUMMARY")
        print("="*60)

        print(f"\nComponents ({len(self.components)}):")
        for designator, comp in sorted(self.components.items()):
            print(f"  {designator:10s} - {comp.library_reference:20s} "
                  f"Value: {comp.value or 'N/A':15s} "
                  f"Pins: {len(comp.pins)}")

        print(f"\nNets ({len(self.nets)}):")
        for net_name, net in sorted(self.nets.items()):
            net_type = ""
            if net.is_power:
                net_type = " [POWER]"
            elif net.is_ground:
                net_type = " [GROUND]"

            print(f"  {net_name:30s}{net_type} - {len(net.pins)} connections")
            for designator, pin in net.pins:
                comp = self.components.get(designator)
                pin_name = comp.pins.get(pin, pin) if comp else pin
                print(f"      {designator}.{pin} ({pin_name})")

        print("="*60)


def main():
    """Command-line interface"""
    import argparse

    parser = argparse.ArgumentParser(
        description='Convert Altium SchDoc to SKiDL/KiCad'
    )
    parser.add_argument('input', help='Input Altium SchDoc file')
    parser.add_argument('-o', '--output', default='schematic.py',
                       help='Output SKiDL file (default: schematic.py)')
    parser.add_argument('--pcb', default='output.kicad_pcb',
                       help='Output KiCad PCB file (default: output.kicad_pcb)')
    parser.add_argument('--netlist', default='output.net',
                       help='Output netlist file (default: output.net)')
    parser.add_argument('--no-execute', action='store_true',
                       help='Do not execute SKiDL code (only generate)')
    parser.add_argument('--summary', action='store_true',
                       help='Print detailed analysis summary')

    args = parser.parse_args()

    # Convert
    converter = AltiumToSKiDLConverter(args.input)
    converter.convert(
        skidl_output=args.output,
        pcb_output=args.pcb,
        netlist_output=args.netlist,
        execute=not args.no_execute
    )

    # Print summary if requested
    if args.summary:
        converter.print_analysis_summary()

    print("\n✓ Conversion complete!")


if __name__ == '__main__':
    main()
