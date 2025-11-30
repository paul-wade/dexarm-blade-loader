"""
States - Individual state definitions for pick-and-place workflow
Each state does ONE thing (Single Responsibility)
"""

from typing import Optional
from .state_machine import State, StateContext, StateResult


class IdleState(State):
    """Idle state - waiting for commands"""
    name = "IDLE"
    
    def on_enter(self, context: StateContext) -> StateResult:
        self.log(context, "Ready")
        return StateResult.SUCCESS
    
    def get_next_state(self, context: StateContext, result: StateResult) -> Optional[State]:
        return None  # Stay idle until external command


class LiftToSafeZState(State):
    """Move to above pick position (XYZ in one move like working code)"""
    name = "LIFT_TO_SAFE_Z"
    
    def on_enter(self, context: StateContext) -> StateResult:
        pick = context.positions.get_pick()
        if not pick:
            self.log(context, "ERROR: No pick position set!")
            return StateResult.FAILURE
        
        safe_z = context.positions.get_safe_z()
        self.log(context, f"→ Moving to above pick ({pick.x:.1f}, {pick.y:.1f}, {safe_z:.1f})")
        # Move XYZ together in one command (matches working code)
        context.arm.move_to(pick.x, pick.y, safe_z)
        return StateResult.SUCCESS
    
    def get_next_state(self, context: StateContext, result: StateResult) -> Optional[State]:
        # Skip MoveToPickXYState - we already moved XY
        return ActivateSuctionState()


class ActivateSuctionState(State):
    """Turn on suction before lowering to pick"""
    name = "ACTIVATE_SUCTION"
    
    def on_enter(self, context: StateContext) -> StateResult:
        self.log(context, "✓ Suction ON")
        context.suction.on()
        return StateResult.SUCCESS
    
    def get_next_state(self, context: StateContext, result: StateResult) -> Optional[State]:
        return LowerToPickState()


class LowerToPickState(State):
    """Lower to pick Z position"""
    name = "LOWER_TO_PICK"
    
    def on_enter(self, context: StateContext) -> StateResult:
        pick = context.positions.get_pick()
        self.log(context, f"↓ Lowering to pick Z={pick.z:.1f}mm")
        context.arm.move_z(pick.z)
        return StateResult.SUCCESS
    
    def get_next_state(self, context: StateContext, result: StateResult) -> Optional[State]:
        return GrabBladeState()


class GrabBladeState(State):
    """Wait for suction to grab blade"""
    name = "GRAB_BLADE"
    
    def on_enter(self, context: StateContext) -> StateResult:
        import time
        self.log(context, "⏱ Grabbing blade...")
        time.sleep(0.5)  # Wait for suction to grab
        return StateResult.SUCCESS
    
    def get_next_state(self, context: StateContext, result: StateResult) -> Optional[State]:
        return LiftWithBladeState()


class LiftWithBladeState(State):
    """Move to above hook position with blade (XYZ in one move like working code)"""
    name = "LIFT_WITH_BLADE"
    
    def on_enter(self, context: StateContext) -> StateResult:
        hook = context.positions.get_hook(context.current_hook_index)
        if not hook:
            self.log(context, f"ERROR: Invalid hook index {context.current_hook_index}")
            return StateResult.FAILURE
        
        safe_z = context.positions.get_safe_z()
        self.log(context, f"→ Moving to above hook {context.current_hook_index} ({hook.x:.1f}, {hook.y:.1f}, {safe_z:.1f})")
        # Move XYZ together in one command (matches working code)
        context.arm.move_to(hook.x, hook.y, safe_z)
        return StateResult.SUCCESS
    
    def get_next_state(self, context: StateContext, result: StateResult) -> Optional[State]:
        # Skip MoveToHookXYState - we already moved XY
        return LowerToHookState()


class LowerToHookState(State):
    """Lower to hook Z position"""
    name = "LOWER_TO_HOOK"
    
    def on_enter(self, context: StateContext) -> StateResult:
        hook = context.positions.get_hook(context.current_hook_index)
        self.log(context, f"↓ Lowering to hook Z={hook.z:.1f}mm")
        context.arm.move_z(hook.z)
        return StateResult.SUCCESS
    
    def get_next_state(self, context: StateContext, result: StateResult) -> Optional[State]:
        return ReleaseBladeState()


class ReleaseBladeState(State):
    """Release blade onto hook"""
    name = "RELEASE_BLADE"
    
    def on_enter(self, context: StateContext) -> StateResult:
        self.log(context, "✓ Releasing blade")
        context.suction.release()
        return StateResult.SUCCESS
    
    def get_next_state(self, context: StateContext, result: StateResult) -> Optional[State]:
        return LiftFromHookState()


class LiftFromHookState(State):
    """Lift back to safe Z after placing blade"""
    name = "LIFT_FROM_HOOK"
    
    def on_enter(self, context: StateContext) -> StateResult:
        safe_z = context.positions.get_safe_z()
        self.log(context, f"↑ Lifting to Z={safe_z:.1f}mm")
        context.arm.move_z(safe_z)
        
        # Update progress
        context.current_hook_index += 1
        if context.on_progress:
            context.on_progress(context.current_hook_index, context.total_hooks)
        
        return StateResult.SUCCESS
    
    def get_next_state(self, context: StateContext, result: StateResult) -> Optional[State]:
        # Check if more hooks to process
        if context.current_hook_index < context.total_hooks:
            self.log(context, f"── Blade {context.current_hook_index + 1}/{context.total_hooks} ──")
            return LiftToSafeZState()  # Loop back to pick next blade
        else:
            return HomingState()


class HomingState(State):
    """Return to home position"""
    name = "HOMING"
    
    def on_enter(self, context: StateContext) -> StateResult:
        self.log(context, "→ Going home")
        context.suction.off()
        
        # SAFETY: ALWAYS lift Z to safe height before XY movement
        safe_z = context.positions.get_safe_z()
        if safe_z is not None:
            self.log(context, f"↑ Lifting to safe Z={safe_z:.1f}mm first")
            context.arm.move_z(safe_z)
        
        context.arm.home()
        return StateResult.SUCCESS
    
    def get_next_state(self, context: StateContext, result: StateResult) -> Optional[State]:
        return CycleCompleteState()


class CycleCompleteState(State):
    """Cycle complete - return to idle"""
    name = "CYCLE_COMPLETE"
    
    def on_enter(self, context: StateContext) -> StateResult:
        self.log(context, "✓ CYCLE COMPLETE")
        return StateResult.SUCCESS
    
    def get_next_state(self, context: StateContext, result: StateResult) -> Optional[State]:
        return None  # End of cycle


# === Workflow factory ===

def create_pick_place_workflow() -> State:
    """Create the initial state for a pick-and-place workflow"""
    return LiftToSafeZState()
