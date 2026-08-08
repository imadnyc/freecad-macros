# SPDX-License-Identifier: LGPL-2.1-or-later
"""Headless checks for the selection macros' geometry cores.

Run with the PieMenu dev shell's freecadcmd:

    cd /home/dre/Projects/PieMenu && \
        nix develop -c freecadcmd /home/dre/Projects/freecad-macros/dev/test_selection.py

Prints SELECTION-TESTS-PASS only if every assert held.  The macros' GUI
glue is gated on FreeCAD.GuiUp, so exec'ing them here only defines the
pure-geometry functions.
"""

import os
import traceback

import FreeCAD  # noqa: F401  (freecadcmd provides it; keeps intent explicit)
import Part

HERE = os.path.dirname(os.path.abspath(__file__))


def load_macro(name):
    path = os.path.join(HERE, os.pardir, "selection", name)
    with open(path) as fh:
        src = fh.read()
    ns = {"__name__": "macro_under_test", "__file__": path}
    exec(compile(src, path, "exec"), ns)
    return ns


def hashes(shapes):
    return {s.hashCode() for s in shapes}


def filleted_box():
    box = Part.makeBox(10.0, 10.0, 10.0)
    vertical = [e for e in box.Edges
                if abs(e.Vertexes[0].Point.z - e.Vertexes[1].Point.z) > 9.0]
    assert len(vertical) == 4
    return box.makeFillet(2.0, vertical)


def loop_edges(shape, z):
    """Edges whose vertices all sit at height z (the top/bottom boundary loop)."""
    return [e for e in shape.Edges
            if e.Vertexes
            and all(abs(v.Point.z - z) < 1e-6 for v in e.Vertexes)]


def line_seed(edges):
    return next(e for e in edges if type(e.Curve).__name__ == "Line")


def main():
    edges_ns = load_macro("SelectTangentEdges.FCMacro")
    faces_ns = load_macro("SelectTangentFaces.FCMacro")
    alt_ns = load_macro("AltChainSelect.FCMacro")
    edge_chain = edges_ns["tangent_edge_chain"]
    face_chain = faces_ns["tangent_face_chain"]

    fb = filleted_box()
    assert len(fb.Edges) == 24 and len(fb.Faces) == 10

    top = loop_edges(fb, 10.0)
    bottom = loop_edges(fb, 0.0)
    assert len(top) == 8 and len(bottom) == 8
    vertical = hashes(fb.Edges) - hashes(top) - hashes(bottom)
    assert len(vertical) == 8

    # (a) one top line seed -> exactly the 8-edge top loop, no verticals
    got = edge_chain(fb, [line_seed(top)])
    assert hashes(got) == hashes(top)
    assert not hashes(got) & vertical
    got = edge_chain(fb, [line_seed(bottom)])
    assert hashes(got) == hashes(bottom)

    # multiple seeds at once: both loops, still no verticals
    got = edge_chain(fb, [line_seed(top), line_seed(bottom)])
    assert hashes(got) == hashes(top) | hashes(bottom)

    # (b) cylinder: closed circles chain to themselves, seam is harmless
    cyl = Part.makeCylinder(5.0, 10.0)
    top_circle = next(e for e in cyl.Edges
                      if type(e.Curve).__name__ == "Circle"
                      and abs(e.Vertexes[0].Point.z - 10.0) < 1e-6)
    got = edge_chain(cyl, [top_circle])
    assert hashes(got) == {top_circle.hashCode()}
    seam = next(e for e in cyl.Edges if type(e.Curve).__name__ == "Line")
    got = edge_chain(cyl, [seam])
    assert hashes(got) == {seam.hashCode()}

    # zero-length degenerate edges (sphere poles) must not break the chain
    sphere = Part.makeSphere(5.0)
    meridian = max(sphere.Edges, key=lambda e: e.Length)
    got = edge_chain(sphere, [meridian])
    assert meridian.hashCode() in hashes(got)

    # (c) face chain: one side face -> all 8 side faces, never top/bottom
    def face_at_z(shape, z):
        return [f for f in shape.Faces
                if all(abs(v.Point.z - z) < 1e-6 for v in f.Vertexes)]

    top_face = face_at_z(fb, 10.0)
    bottom_face = face_at_z(fb, 0.0)
    assert len(top_face) == 1 and len(bottom_face) == 1
    sides = hashes(fb.Faces) - hashes(top_face) - hashes(bottom_face)
    assert len(sides) == 8
    seed_face = next(f for f in fb.Faces
                     if f.hashCode() in sides
                     and type(f.Surface).__name__ == "Plane")
    got = face_chain(fb, [seed_face])
    assert hashes(got) == sides

    # cylinder wall stops at the caps; its seam maps the wall to itself
    wall = next(f for f in cyl.Faces
                if type(f.Surface).__name__ == "Cylinder")
    got = face_chain(cyl, [wall])
    assert hashes(got) == {wall.hashCode()}

    # (d) tolerance: plain box, every corner is 90 deg -> nothing chains
    box = Part.makeBox(10.0, 10.0, 10.0)
    for tol in (5.0, 0.0):
        got = edge_chain(box, [box.Edges[0]], tol)
        assert hashes(got) == {box.Edges[0].hashCode()}, f"tol={tol}"
    # sanity that tolerance is really the knob: past 90 deg it all connects
    got = edge_chain(box, [box.Edges[0]], 91.0)
    assert hashes(got) == hashes(box.Edges)

    # AltChainSelect carries identical copies of both cores
    got = alt_ns["tangent_edge_chain"](fb, [line_seed(top)])
    assert hashes(got) == hashes(top)
    got = alt_ns["tangent_face_chain"](fb, [seed_face])
    assert hashes(got) == sides

    # (e) boundary loop on the plain box: a box edge borders two faces, so
    # a bare seed is ambiguous (some 4-edge loop containing it); a second
    # context edge makes the top face's loop win by the scoring rule
    loop_ns = load_macro("SelectBoundaryLoop.FCMacro")
    boundary_loop = loop_ns["boundary_loop"]
    box_top = loop_edges(box, 10.0)
    assert len(box_top) == 4
    seed = box_top[0]
    face, loop = boundary_loop(box, seed, [seed])
    assert face is not None and len(loop) == 4
    assert seed.hashCode() in hashes(loop)
    face, loop = boundary_loop(box, seed, [seed, box_top[1]])
    assert hashes(loop) == hashes(box_top)
    assert all(abs(v.Point.z - 10.0) < 1e-6 for v in face.Vertexes)

    # (f) SelectFaceEdges: a box face yields exactly its 4 edges
    fedges_ns = load_macro("SelectFaceEdges.FCMacro")
    got = fedges_ns["face_edges"]([box.Faces[0]])
    assert len(got) == 4 and hashes(got) == hashes(box.Faces[0].Edges)

    # (g) cylinder seam dedupe: the wall's wire may list the seam twice
    # (OCC convention); the loop result contains it exactly once
    face, loop = boundary_loop(cyl, seam)
    assert type(face.Surface).__name__ == "Cylinder"
    loop_hashes = [e.hashCode() for e in loop]
    assert len(loop_hashes) == len(set(loop_hashes)) == 3
    assert loop_hashes.count(seam.hashCode()) == 1

    # the AngleTolerance parameter read works headless; the value comes
    # from the user's config (5.0 when unset), so only check the plumbing
    for ns in (edges_ns, faces_ns, alt_ns):
        tol = ns["_tolerance"]()
        assert isinstance(tol, float) and tol > 0.0

    print("SELECTION-TESTS-PASS")


try:
    main()
except Exception:
    traceback.print_exc()
    print("SELECTION-TESTS-FAIL")
