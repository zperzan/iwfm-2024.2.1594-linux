#!/usr/bin/env python3
"""Regenerate cmake/IWFMSources.cmake from IWFM 2024.2.1594 .vfproj files.

Usage: python3 tools/generate_sources.py
Only standard-library modules are required. Run with the 2024 source tree intact.
"""
from pathlib import Path
import posixpath
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parent.parent
PROJECTS = {
    'PreProcessor': 'PreProcessor/PreProcessor.vfproj',
    'Simulation': 'Simulation/Simulation.vfproj',
    'Simulation_Parallel': 'Simulation_Parallel/Simulation_Parallel.vfproj',
    'Simulation_MM': 'Simulation_MM/Simulation_MM.vfproj',
    'Budget': 'Budget/Budget.vfproj',
    'ZBudget': 'ZBudget/Z-Budget.vfproj',
    'IWFM_C': 'IWFM_DLL/IWFM_C_DLL_Heap.vfproj',
}


def generate():
    manifests, directories = {}, set()
    for name, project_path in PROJECTS.items():
        project = ROOT / project_path
        if not project.is_file():
            raise FileNotFoundError(project)
        paths = []
        for item in ET.parse(project).findall('.//File'):
            raw = item.attrib.get('RelativePath', '').replace('\\', '/')
            if not raw.lower().endswith(('.f', '.f90', '.for', '.fpp')):
                continue
            rel = posixpath.normpath(posixpath.join(posixpath.dirname(project_path), raw))
            if rel.endswith('Opening_screen_WINDOWS.f90'):
                rel = rel.replace('Opening_screen_WINDOWS.f90', 'Opening_screen_LINUX.f90')
            if rel.startswith('../') or not (ROOT / rel).is_file():
                raise FileNotFoundError(f'{name} references nonexistent source: {rel}')
            paths.append(rel)
            directories.add(posixpath.dirname(rel))
        if len(paths) != len(set(paths)):
            raise ValueError(f'Duplicate source in {project_path}')
        manifests[name] = paths

    lines = [
        '# Auto-generated from the original Intel Visual Fortran project files.',
        '# Regenerate: python3 tools/generate_sources.py',
        '# Relative paths are rooted at IWFM source tree.',
    ]
    for name, sources in manifests.items():
        lines.extend(['', f'set(IWFM_SOURCES_{name}'])
        lines.extend(f'  "${{CMAKE_CURRENT_SOURCE_DIR}}/{p}"' for p in sources)
        lines.append(')')
    lines.extend(['', 'set(IWFM_FORTRAN_INCLUDE_DIRS'])
    lines.extend(f'  "${{CMAKE_CURRENT_SOURCE_DIR}}/{p}"' for p in sorted(directories))
    lines.append(')')
    outfile = ROOT / 'cmake/IWFMSources.cmake'
    outfile.parent.mkdir(parents=True, exist_ok=True)
    outfile.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    for name, sources in manifests.items():
        print(f'{name}: {len(sources)} Fortran files')
    print(f'Created {outfile.relative_to(ROOT)} ({len(directories)} include directories)')


if __name__ == '__main__':
    generate()
