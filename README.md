# freecad-macros

Small standalone FreeCAD macros. Each one is a single file: grab the one
you want, drop it in your macro folder, done.

> **Heads up:** these macros were generated with AI. I use them and they
> work for me, but I haven't vetted every line — try them on something
> you can afford to lose first.

## selection/

Plasticity-style smart selection: pick one thing, get the whole smooth
chain.

* **SelectTangentEdges.FCMacro** — grows your selected edge(s) along
  tangent-continuous chains. One click on a filleted top loop plus this
  macro selects the whole loop; at T-junctions every smooth branch is
  followed. Works with several seeds and across several objects at once.
* **SelectTangentFaces.FCMacro** — the same for faces: grows the
  selection across edges where the surfaces meet smoothly (G1). On a
  filleted box, one side face sweeps around all four sides through the
  fillets and stops before the top and bottom.
* **AltChainSelect.FCMacro** — a toggle. While it's on, picking an edge
  or face with **Alt** held selects its whole chain automatically;
  normal picks are untouched. Run the macro again to turn it off.
* **SelectBoundaryLoop.FCMacro** — loop is not tangency: a rectangular
  pocket floor has a boundary loop but zero tangency. This selects the
  closed wire a selected edge belongs to on an adjacent face. An edge
  always borders two faces, so two loops qualify — the one sharing the
  most edges with your current selection wins (select a second edge of
  the loop you mean to disambiguate), and the console says which face's
  loop was taken.
* **SelectFaceEdges.FCMacro** — all edges of the selected face(s).
  FreeCAD makes faces easy to pick and their thin edges hard
  ([FreeCAD issue #29353](https://github.com/FreeCAD/FreeCAD/issues/29353));
  this closes the gap.

The tangency macros share one tolerance: the float parameter
`AngleTolerance` (degrees) under `User parameter:BaseApp/SmartSelect`,
default 5. Set it once in Tools → Edit parameters… (add the
`SmartSelect` group and a float `AngleTolerance` if not there yet) and
the whole suite follows; real-world G1 joints often measure a fraction
of a degree off, so tighten or loosen to taste.

## Install

Copy the `.FCMacro` files into your macro directory — find it under
Edit → Preferences → Python → Macro, or ask the Python console:
`FreeCAD.getUserMacroDir()`. They then show up under Macro → Macros….
(Once this repo has releases you'll also be able to point the Addon
Manager at it as a custom repository.)

## Bind them to gestures

These pair well with the [PieMenu v2 addon](https://github.com/imadnyc/PieMenu):
put a macro in any pie slot (macros as slot targets) or bind one
straight to a key, so a flick of the mouse grabs a whole tangent loop.

## License

LGPL-2.1-or-later, same as FreeCAD. See [`License`](License).
