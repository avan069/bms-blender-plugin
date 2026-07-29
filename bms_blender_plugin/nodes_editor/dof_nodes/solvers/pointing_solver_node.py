import math

import bpy
from bpy.props import PointerProperty

from bms_blender_plugin.common.blender_types import BlenderEditorNodeType
from bms_blender_plugin.common.bml_structs import MathOp, ArgType, RenderControlMath, RenderControlNode
from bms_blender_plugin.common.resolve_ids import resolve_dof_number
from bms_blender_plugin.nodes_editor.dof_base_node import DofBaseNode, subscribe_node, unsubscribe_node


class NodePointingSolver(DofBaseNode):
    """Solver node that drives a rotation DOF to point at a target empty.

    The pivot position is taken from the rotation DOF's world location.
    The computed angle (atan2 of the XY displacement) is written to the
    rotation DOF's dof_input for live viewport preview.

    At export, if the target is static the current angle is baked as a
    constant SET render control. A warning is printed to alert the user that
    the exported value will only be correct for the current target position.
    """

    bl_label = "Pointing Solver"
    bl_description = "Points a rotation DOF toward a target empty"
    bl_icon = "ORIENTATION_GIMBAL"

    solver_rot_dof: PointerProperty(name="Rotation DOF", type=bpy.types.Object)
    solver_target: PointerProperty(name="Target", type=bpy.types.Object)

    def init(self, context):
        self.bml_node_type = str(BlenderEditorNodeType.SOLVER)
        self.width = 300

    def draw_buttons(self, context, layout):
        layout.prop(self, "solver_rot_dof")
        layout.prop(self, "solver_target")

        if self.solver_rot_dof and self.solver_target:
            dof_loc = self.solver_rot_dof.matrix_world.to_translation()
            target_loc = self.solver_target.matrix_world.to_translation()
            dx = target_loc.x - dof_loc.x
            dy = target_loc.y - dof_loc.y
            angle_deg = math.degrees(math.atan2(dy, dx))
            layout.label(text=f"Angle: {round(angle_deg, 2)}°")

    def execute(self, context):
        if not self.solver_rot_dof or not self.solver_target:
            return

        dof_loc = self.solver_rot_dof.matrix_world.to_translation()
        target_loc = self.solver_target.matrix_world.to_translation()

        dx = target_loc.x - dof_loc.x
        dy = target_loc.y - dof_loc.y

        angle = math.atan2(dy, dx)
        self.solver_rot_dof.dof_input = angle

    def generate_rc_nodes(self, node_start_index):
        """Generate RC nodes for export. Bakes the current angle as a constant SET node."""
        if not self.solver_rot_dof or not self.solver_target:
            return []

        dof_number = resolve_dof_number(self.solver_rot_dof)
        if dof_number is None:
            print(f"WARNING: Pointing Solver '{self.name}': rotation DOF has no resolved DOF number — skipping export.")
            return []

        dof_loc = self.solver_rot_dof.matrix_world.to_translation()
        target_loc = self.solver_target.matrix_world.to_translation()

        dx = target_loc.x - dof_loc.x
        dy = target_loc.y - dof_loc.y
        angle = math.atan2(dy, dx)

        print(
            f"WARNING: Pointing Solver '{self.name}': target '{self.solver_target.name}' is treated as static. "
            f"The exported RC will only be correct for the current target position."
        )

        rc_math = RenderControlMath(
            math_op=MathOp.SET,
            arguments=[(ArgType.FLOAT, float(angle))],
            result_type=ArgType.DOF_ID,
            result_id=dof_number,
        )
        rc = RenderControlNode(node_start_index)
        rc.rc_math = rc_math
        return [rc]


def register():
    bpy.utils.register_class(NodePointingSolver)
    subscribe_node(NodePointingSolver)


def unregister():
    unsubscribe_node(NodePointingSolver)
    bpy.utils.unregister_class(NodePointingSolver)


bpy.types.Node.solver_rot_dof = bpy.props.PointerProperty(name="Rotation DOF", type=bpy.types.Object)
bpy.types.Node.solver_target = bpy.props.PointerProperty(name="Target", type=bpy.types.Object)
