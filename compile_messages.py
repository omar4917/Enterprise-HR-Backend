"""
Compile .po files to .mo files using Python's tools module.
This script is a workaround for Windows systems without gettext installed.
"""
import os
import sys

# Add the Python Tools directory to path for msgfmt
tools_path = os.path.join(os.path.dirname(sys.executable), 'Tools', 'i18n')
if os.path.exists(tools_path):
    sys.path.insert(0, tools_path)

# Try to use the bundled msgfmt from Python
try:
    from Tools.i18n import msgfmt
except ImportError:
    try:
        import msgfmt
    except ImportError:
        # Manual minimal implementation
        print("Using manual .mo compilation...")
        import struct

        def compile_po_to_mo(po_path, mo_path):
            """Minimal PO to MO compiler"""
            with open(po_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Parse entries
            entries = {}
            current_msgid = None
            current_msgstr = None
            
            for line in content.split('\n'):
                line = line.strip()
                if line.startswith('msgid "'):
                    if current_msgid is not None and current_msgstr is not None:
                        entries[current_msgid] = current_msgstr
                    current_msgid = line[7:-1]
                    current_msgstr = None
                elif line.startswith('msgstr "'):
                    current_msgstr = line[8:-1]
                elif line.startswith('"') and line.endswith('"'):
                    if current_msgstr is not None:
                        current_msgstr += line[1:-1]
                    elif current_msgid is not None:
                        current_msgid += line[1:-1]
            
            if current_msgid is not None and current_msgstr is not None:
                entries[current_msgid] = current_msgstr
            
            # Remove empty msgid (header)
            if '' in entries:
                del entries['']
            
            # Sort keys
            keys = sorted(entries.keys())
            
            # Build MO file
            offsets = []
            ids = b''
            strs = b''
            
            for key in keys:
                key_bytes = key.encode('utf-8')
                val_bytes = entries[key].encode('utf-8')
                offsets.append((len(ids), len(key_bytes), len(strs), len(val_bytes)))
                ids += key_bytes + b'\x00'
                strs += val_bytes + b'\x00'
            
            # MO file header
            n_entries = len(keys)
            keystart = 7 * 4
            valuestart = keystart + n_entries * 8
            
            output = []
            output.append(struct.pack('I', 0x950412de))  # Magic
            output.append(struct.pack('I', 0))  # Version
            output.append(struct.pack('I', n_entries))  # Number of entries
            output.append(struct.pack('I', keystart))  # Offset of key table
            output.append(struct.pack('I', valuestart))  # Offset of value table
            output.append(struct.pack('I', 0))  # Size of hashing table
            output.append(struct.pack('I', 0))  # Offset of hashing table
            
            # Key table
            ids_start = valuestart + n_entries * 8
            strs_start = ids_start + len(ids)
            
            for o in offsets:
                output.append(struct.pack('II', o[1], ids_start + o[0]))
            for o in offsets:
                output.append(struct.pack('II', o[3], strs_start + o[2]))
            
            output.append(ids)
            output.append(strs)
            
            with open(mo_path, 'wb') as f:
                f.write(b''.join(output))
            
            print(f"Compiled: {po_path} -> {mo_path}")

        # Compile all .po files
        import pathlib
        locale_dir = pathlib.Path(__file__).parent / 'locale'
        for po_file in locale_dir.rglob('*.po'):
            mo_file = po_file.with_suffix('.mo')
            compile_po_to_mo(str(po_file), str(mo_file))
        
        print("All .po files compiled!")
        sys.exit(0)

# If msgfmt is available, use it
import pathlib
locale_dir = pathlib.Path(__file__).parent / 'locale'
for po_file in locale_dir.rglob('*.po'):
    mo_file = po_file.with_suffix('.mo')
    msgfmt.make(str(po_file), str(mo_file))
    print(f"Compiled: {po_file} -> {mo_file}")

print("All .po files compiled!")
