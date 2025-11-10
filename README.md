
.venv: `& D:/repo/pitin/altium_schdoc_editor/.venv/Scripts/Activate.ps1`
.env skidl environment 참고

# Tell SKiDL where the symbol libraries are.
`lib_search_paths['kicad'].append('C:/Program Files/KiCad/9.0/share/kicad/symbols')`

## Altium ➜ SKiDL ➜ KiCad Workflow

```powershell
# Convert an Altium schematic into a standalone SKiDL script.
python schdoc_to_skidl.py .\Design.SchDoc --output .\Design_skidl.py

# Export KiCad artefacts (netlist/PCB) from the generated SKiDL file.
python skidl_to_kicad.py .\Design_skidl.py --netlist .\Design.net --pcb .\Design.kicad_pcb
```

Pass `--skip-erc` to `skidl_to_kicad.py` if you want to skip the electrical rule
check, or omit `--pcb` when you only need a netlist.
