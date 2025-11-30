"""
Motion Planner - Single responsibility: planning motion sequences.

Task 1.2: Motion Planner

This module converts high-level movement goals into sequences of commands
that satisfy safety invariants. It does NOT execute commands.

Key Invariants Enforced:
- INV-M1: Safe moves lift Z before XY motion
- INV-M2: No low XY motion when carrying blade
- INV-M3: Wait after every move command
- INV-M4: All positions within workspace limits
"""

from typing import List, Tuple, Union

from .types import (
    Command,
    DelayCommand,
    MoveCommand,
    Position,
    SuctionCommand,
    WaitCommand,
    WorkspaceLimits,
    DEFAULT_WORKSPACE,
)


# Type alias for command sequences
CommandSequence = List[Union[MoveCommand, WaitCommand, SuctionCommand, DelayCommand]]


class MotionPlanner:
    """
    Plans motion sequences that satisfy safety invariants.
    
    All planning methods return command sequences that:
    1. Move Z to safe height before XY motion (when needed)
    2. Include M400 wait after every move
    3. Validate all positions against workspace limits
    """

    def __init__(
        self,
        safe_z: float = 50.0,
        feedrate: int = 3000,
        workspace: WorkspaceLimits = DEFAULT_WORKSPACE,
    ):
        self.safe_z = safe_z
        self.feedrate = feedrate
        self.workspace = workspace

    def _validate_position(self, pos: Position) -> None:
        """Raise ValueError if position is outside workspace."""
        valid, msg = self.workspace.validate(pos)
        if not valid:
            raise ValueError(f"Position invalid: {msg}")

    def plan_direct_move(self, target: Position) -> CommandSequence:
        """
        Plan a direct move (single G1 with XYZ).
        
        Use when already at safe Z or when exact path doesn't matter.
        Always includes wait command.
        """
        self._validate_position(target)
        
        return [
            MoveCommand(x=target.x, y=target.y, z=target.z, feedrate=self.feedrate),
            WaitCommand(),
        ]

    def plan_safe_move(
        self, current: Position, target: Position
    ) -> CommandSequence:
        """
        Plan a safe move: Z-up → XY → Z-down.
        
        This prevents collisions by lifting before any horizontal motion.
        
        Sequence:
        1. If current.z < safe_z: lift to safe_z first
        2. Move XY to target XY (staying at safe_z or higher)
        3. Lower Z to target.z
        
        Each move is followed by M400 wait.
        """
        self._validate_position(target)
        
        commands: CommandSequence = []
        
        # Step 1: Lift to safe_z if below
        if current.z < self.safe_z:
            commands.append(MoveCommand(z=self.safe_z, feedrate=self.feedrate))
            commands.append(WaitCommand())
        
        # Step 2: Move XY if needed (at safe height)
        if current.x != target.x or current.y != target.y:
            commands.append(
                MoveCommand(x=target.x, y=target.y, feedrate=self.feedrate)
            )
            commands.append(WaitCommand())
        
        # Step 3: Lower to target Z if needed
        move_z = max(current.z, self.safe_z)  # Current Z after lift
        if target.z != move_z:
            commands.append(MoveCommand(z=target.z, feedrate=self.feedrate))
            commands.append(WaitCommand())
        
        # If no commands generated (same position), still return valid sequence
        if not commands:
            commands.append(WaitCommand())
        
        return commands

    def plan_pick_sequence(
        self, current: Position, pick_pos: Position, vacuum_delay_ms: int = 200
    ) -> CommandSequence:
        """
        Plan a complete pick sequence.
        
        Steps:
        1. Safe move to above pick position
        2. Turn on suction
        3. Lower to pick position
        4. Wait for vacuum to establish
        5. Lift to safe Z
        """
        self._validate_position(pick_pos)
        
        commands: CommandSequence = []
        
        # Move safely to above pick position
        above_pick = pick_pos.with_z(self.safe_z)
        commands.extend(self.plan_safe_move(current, above_pick))
        
        # Turn on suction BEFORE lowering
        commands.append(SuctionCommand("on"))
        
        # Lower to pick position
        commands.append(MoveCommand(z=pick_pos.z, feedrate=self.feedrate))
        commands.append(WaitCommand())
        
        # Wait for vacuum
        commands.append(DelayCommand(milliseconds=vacuum_delay_ms))
        
        # Lift to safe Z
        commands.append(MoveCommand(z=self.safe_z, feedrate=self.feedrate))
        commands.append(WaitCommand())
        
        return commands

    def plan_place_sequence(
        self, current: Position, place_pos: Position, release_delay_ms: int = 100
    ) -> CommandSequence:
        """
        Plan a complete place sequence.
        
        Steps:
        1. Safe move to above place position
        2. Lower to place position
        3. Release suction
        4. Wait for release
        5. Turn off pump
        6. Lift to safe Z
        """
        self._validate_position(place_pos)
        
        commands: CommandSequence = []
        
        # Move safely to above place position
        above_place = place_pos.with_z(self.safe_z)
        commands.extend(self.plan_safe_move(current, above_place))
        
        # Lower to place position
        commands.append(MoveCommand(z=place_pos.z, feedrate=self.feedrate))
        commands.append(WaitCommand())
        
        # Blow air to release blade (M1001)
        commands.append(SuctionCommand("blow"))
        
        # Wait for blade to release
        commands.append(DelayCommand(milliseconds=release_delay_ms))
        
        # Stop pump
        commands.append(SuctionCommand("off"))
        
        # Lift to safe Z
        commands.append(MoveCommand(z=self.safe_z, feedrate=self.feedrate))
        commands.append(WaitCommand())
        
        return commands


# =============================================================================
# Invariant Verification Functions
# =============================================================================


def verify_safe_move_invariant(
    commands: CommandSequence, start_position: Position, safe_z: float
) -> Tuple[bool, str]:
    """
    Verify INV-M1: Safe moves lift Z before XY motion.
    
    If starting below safe_z and there's XY motion, the first move
    must be a Z-only lift to at least safe_z.
    """
    if start_position.z >= safe_z:
        # Already at safe height, no lift required
        return True, "Already at safe Z"
    
    # Find first XY-changing move
    first_xy_index = None
    first_z_up_index = None
    
    for i, cmd in enumerate(commands):
        if isinstance(cmd, MoveCommand):
            if cmd.changes_xy() and first_xy_index is None:
                first_xy_index = i
            if cmd.is_z_only() and cmd.z is not None and first_z_up_index is None:
                # Check if this Z move goes up
                if cmd.z >= safe_z:
                    first_z_up_index = i
    
    # If there's XY motion, Z lift must come first
    if first_xy_index is not None:
        if first_z_up_index is None:
            return False, "XY motion without prior Z lift to safe height"
        if first_z_up_index > first_xy_index:
            return False, f"Z lift (idx {first_z_up_index}) after XY motion (idx {first_xy_index})"
    
    return True, "OK"


def verify_wait_after_moves(commands: CommandSequence) -> Tuple[bool, str]:
    """
    Verify INV-M3: Every move command has wait before next move.
    
    The sequence [MOVE, MOVE] is invalid.
    The sequence [MOVE, WAIT, MOVE] is valid.
    """
    prev_was_move = False
    
    for i, cmd in enumerate(commands):
        if isinstance(cmd, MoveCommand):
            if prev_was_move:
                return False, f"Consecutive moves at index {i-1} and {i} without wait"
            prev_was_move = True
        elif isinstance(cmd, WaitCommand):
            prev_was_move = False
        # Other commands (Suction, Delay) don't affect this invariant
        # but a delay or suction between moves is fine
        else:
            prev_was_move = False
    
    return True, "OK"
