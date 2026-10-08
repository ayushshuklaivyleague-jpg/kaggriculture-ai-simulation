import json
import base64
import io
import tarfile
import hashlib
import os

def extract():
    print("Reading kaggriculture-a-smaller-market-shock.ipynb...")
    with open('kaggriculture-a-smaller-market-shock.ipynb', 'r', encoding='utf-8') as f:
        nb = json.load(f)
        
    src3 = ''.join(nb['cells'][3]['source'])
    globs = {}
    exec(src3, globs, globs)
    
    for idx, c in enumerate(nb['cells']):
        src = ''.join(c['source'])
        if 'ARCHIVE_BYTES' in src:
            print(f"Found archive in cell {idx}")
            # Locate ARCHIVE_BYTES = base64.b64decode(...)
            # Execute cell or parse b64
            import pathlib
            globs.update({
                'hashlib': hashlib,
                'base64': base64,
                'io': io,
                'tarfile': tarfile,
                'pathlib': pathlib,
                'Path': pathlib.Path,
                'os': os
            })
            loc = {}
            exec(src, globs, loc)
            archive_bytes = loc.get('ARCHIVE_BYTES')
            if archive_bytes:
                with tarfile.open(fileobj=io.BytesIO(archive_bytes), mode='r:gz') as tar:
                    main_bytes = tar.extractfile('main.py').read()
                    print(f"Total extracted main_bytes: {len(main_bytes)}")
                    
                    # 1. Market Shock original
                    with open('opponent_market_shock.py', 'wb') as out_f:
                        out_f.write(main_bytes)
                    print(f"Saved opponent_market_shock.py ({len(main_bytes)} bytes)")
                    
                    # 2. Upstream 2945 farm
                    control_bytes = main_bytes[:856427]
                    h = hashlib.sha256(control_bytes).hexdigest()
                    print(f"Upstream SHA256: {h}")
                    with open('opponent_2945_upstream.py', 'wb') as out_f:
                        out_f.write(control_bytes)
                    print(f"Saved opponent_2945_upstream.py ({len(control_bytes)} bytes)")

if __name__ == '__main__':
    extract()
