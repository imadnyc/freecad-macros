# SPDX-License-Identifier: LGPL-2.1-or-later
"""Headless check for ConvertMeshToSolid: a real STL round-trip comes back
as a valid, refined, watertight solid.

Run (freecadcmd comes from the PieMenu dev shell):

    cd ~/Projects/PieMenu && nix develop -c freecadcmd \
        ~/Projects/freecad-macros/dev/test_convert.py

Prints CONVERT-TESTS-PASS on success.  freecadcmd exits 0 on exceptions,
so grep for the sentinel, never trust the exit code.
"""
import os
import tempfile
import traceback

import FreeCAD  # noqa: F401
import Mesh
import MeshPart
import Part


def load_macro(name):
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "..", "mesh", name)
    ns = {"__name__": "test_convert"}
    with open(path) as fh:
        src = fh.read()
    exec(compile(src, path, "exec"), ns)  # noqa: S102 -- our own file
    return ns


try:
    ns = load_macro("ConvertMeshToSolid.FCMacro")
    p = {"sew": 0.1, "repair": True, "refine": True, "unify": False,
         "warn": 10000, "hide": True}

    # a cylinder with a hole, through actual STL bytes
    cyl = Part.makeCylinder(10, 20).cut(Part.makeCylinder(3, 20))
    mesh = MeshPart.meshFromShape(Shape=cyl, LinearDeflection=0.5,
                                  AngularDeflection=0.5, Relative=False)
    stl = os.path.join(tempfile.gettempdir(), "convert_test.stl")
    mesh.write(stl)
    mesh = Mesh.Mesh(stl)
    notes = []
    shape, watertight = ns["convert"](mesh, p, notes.append)
    assert watertight, notes
    assert shape.isValid()
    assert len(shape.Faces) < mesh.CountFacets / 2, \
        (len(shape.Faces), mesh.CountFacets)      # refine actually refined
    analytic = cyl.Volume
    assert abs(shape.Volume - analytic) / analytic < 0.02, shape.Volume
    print("PASS watertight cylinder")

    # an open mesh comes back as a shell, flagged, not a crash
    open_mesh = Mesh.Mesh()
    open_mesh.addFacet(FreeCAD.Vector(0, 0, 0), FreeCAD.Vector(10, 0, 0),
                       FreeCAD.Vector(0, 10, 0))
    no_repair = dict(p, repair=False)
    notes = []
    shape, watertight = ns["convert"](open_mesh, no_repair, notes.append)
    assert not watertight and any("WATERTIGHT" in n for n in notes), notes
    print("PASS open mesh flagged")

    os.remove(stl)
    print("CONVERT-TESTS-PASS")
except Exception:  # noqa: BLE001 -- freecadcmd swallows tracebacks
    print(traceback.format_exc())
    print("CONVERT-TESTS-FAIL")
