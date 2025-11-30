"""
Motion Orchestration Layer for DexArm
Provides standardized, safe movement primitives and workflows
"""

from enum import Enum
from typing import Optional, Callable, Dict, Tuple
import time


class MotionPolicy(Enum):
    SAFE = "safe"
    DIRECT = "direct"
    RELATIVE = "relative"


class FeedbackMode(Enum):
    SILENT = "silent"
    BEEP = "beep"
    VERBOSE = "verbose"


class MotionOrchestrator:
    
    def __init__(self, controller):
        self.controller = controller
        self.default_policy = MotionPolicy.SAFE
        self.default_feedback = FeedbackMode.BEEP
        
    def _get_safe_z(self) -> float:
        return self.controller.positions.get('safe_z', 0)
    
    def _get_feedrate(self) -> int:
        return self.controller.settings['feedrate']
    
    def _send_cmd(self, cmd: str):
        return self.controller.send_command(cmd)
    
    def _wait_move(self):
        self.controller.wait_for_move()
    
    def _beep(self, feedback: FeedbackMode):
        if feedback == FeedbackMode.BEEP:
            self._send_cmd("M2000")
    
    def _log(self, message: str, callback: Optional[Callable] = None):
        if callback:
            callback(message)
        print(f"[MOTION] {message}")
    
    def move_z_only(self, z: float, feedrate: Optional[int] = None, 
                    callback: Optional[Callable] = None):
        f = feedrate or self._get_feedrate()
        self._log(f"Z → {z:.2f}mm", callback)
        self._send_cmd(f"G1 F{f} Z{z:.2f}")
        self._wait_move()
    
    def move_xy_only(self, x: float, y: float, feedrate: Optional[int] = None,
                     callback: Optional[Callable] = None):
        f = feedrate or self._get_feedrate()
        self._log(f"XY → ({x:.2f}, {y:.2f})", callback)
        self._send_cmd(f"G1 F{f} X{x:.2f} Y{y:.2f}")
        self._wait_move()
    
    def move_xyz_direct(self, x: float, y: float, z: float, 
                       feedrate: Optional[int] = None,
                       callback: Optional[Callable] = None):
        f = feedrate or self._get_feedrate()
        self._log(f"XYZ → ({x:.2f}, {y:.2f}, {z:.2f})", callback)
        self._send_cmd(f"G1 F{f} X{x:.2f} Y{y:.2f} Z{z:.2f}")
        self._wait_move()
        self.controller.current_pos = {'x': x, 'y': y, 'z': z}
    
    def move_to_position(self, x: float, y: float, z: float,
                        policy: Optional[MotionPolicy] = None,
                        feedrate: Optional[int] = None,
                        feedback: Optional[FeedbackMode] = None,
                        callback: Optional[Callable] = None) -> bool:
        policy = policy or self.default_policy
        feedback = feedback or self.default_feedback
        f = feedrate or self._get_feedrate()
        
        self._beep(feedback)
        
        if policy == MotionPolicy.DIRECT:
            self._log("Policy: DIRECT (XYZ simultaneous)", callback)
            self.move_xyz_direct(x, y, z, f, callback)
            
        elif policy == MotionPolicy.SAFE:
            self._log("Policy: SAFE (Z-up → XY → Z-down)", callback)
            safe_z = self._get_safe_z()
            
            self._log(f"  ↑ Lift to safe Z ({safe_z:.2f}mm)", callback)
            self.move_z_only(safe_z, f)
            
            self._log(f"  → Move XY to ({x:.2f}, {y:.2f})", callback)
            self.move_xy_only(x, y, f)
            
            self._log(f"  ↓ Lower to Z ({z:.2f}mm)", callback)
            self.move_z_only(z, f)
            
            self.controller.current_pos = {'x': x, 'y': y, 'z': z}
            
        elif policy == MotionPolicy.RELATIVE:
            self._log("Policy: RELATIVE (from current position)", callback)
            curr = self.controller.current_pos
            target_x = curr['x'] + x
            target_y = curr['y'] + y
            target_z = curr['z'] + z
            self.move_xyz_direct(target_x, target_y, target_z, f, callback)
        
        return True
    
    def lift_to_safe_z(self, feedback: Optional[FeedbackMode] = None,
                      callback: Optional[Callable] = None):
        feedback = feedback or self.default_feedback
        safe_z = self._get_safe_z()
        
        self._beep(feedback)
        self._log(f"↑ Lifting to safe Z ({safe_z:.2f}mm)", callback)
        self.move_z_only(safe_z, callback=callback)
    
    def go_home_safe(self, feedback: Optional[FeedbackMode] = None,
                    callback: Optional[Callable] = None):
        feedback = feedback or self.default_feedback
        
        self._beep(feedback)
        self._log("Going home (safe)", callback)
        
        safe_z = self._get_safe_z()
        if safe_z and safe_z > 0:
            self._log(f"  ↑ Lift to safe Z ({safe_z:.2f}mm)", callback)
            self.move_z_only(safe_z)
        
        self._log("  → Homing (M1112)", callback)
        self._send_cmd("M1112")
        time.sleep(2)
        self.controller.current_pos = {'x': 0, 'y': 300, 'z': 0}
    
    def pick_sequence(self, pick_pos: Dict[str, float],
                     feedback: Optional[FeedbackMode] = None,
                     callback: Optional[Callable] = None) -> bool:
        feedback = feedback or self.default_feedback
        safe_z = self._get_safe_z()
        f = self._get_feedrate()
        
        self._beep(feedback)
        self._log("=== PICK SEQUENCE ===", callback)
        
        self._log(f"  ↑ Lift to safe Z ({safe_z:.2f}mm)", callback)
        self.move_z_only(safe_z, f)
        
        self._log(f"  → Move above pick ({pick_pos['x']:.2f}, {pick_pos['y']:.2f})", callback)
        self.move_xy_only(pick_pos['x'], pick_pos['y'], f)
        
        self._log("  ✓ Suction ON", callback)
        self._send_cmd("M1000")
        time.sleep(0.3)
        
        self._log(f"  ↓ Lower to pick Z ({pick_pos['z']:.2f}mm)", callback)
        self.move_z_only(pick_pos['z'], f)
        
        grab_delay = self.controller.settings['suction_grab_delay']
        self._log(f"  ⏱ Wait {grab_delay}s for suction", callback)
        time.sleep(grab_delay)
        
        self._log(f"  ↑ Lift with blade to safe Z", callback)
        self.move_z_only(safe_z, f)
        
        self._log("✓ Pick complete", callback)
        return True
    
    def place_sequence(self, place_pos: Dict[str, float],
                      feedback: Optional[FeedbackMode] = None,
                      callback: Optional[Callable] = None) -> bool:
        feedback = feedback or self.default_feedback
        safe_z = self._get_safe_z()
        f = self._get_feedrate()
        
        self._log("=== PLACE SEQUENCE ===", callback)
        
        self._log(f"  ↑ Ensure safe Z ({safe_z:.2f}mm)", callback)
        self.move_z_only(safe_z, f)
        
        self._log(f"  → Move above drop ({place_pos['x']:.2f}, {place_pos['y']:.2f})", callback)
        self.move_xy_only(place_pos['x'], place_pos['y'], f)
        
        self._log(f"  ↓ Lower to drop Z ({place_pos['z']:.2f}mm)", callback)
        self.move_z_only(place_pos['z'], f)
        
        self._log("  ✓ Release suction", callback)
        self._send_cmd("M1002")
        time.sleep(0.5)
        self._send_cmd("M1003")
        time.sleep(0.2)
        
        self._log(f"  ↑ Lift to safe Z", callback)
        self.move_z_only(safe_z, f)
        
        self._log("✓ Place complete", callback)
        return True
    
    def validate_position(self, x: float, y: float, z: float) -> Tuple[bool, str]:
        if z < -50 or z > 200:
            return False, f"Z out of range: {z}"
        
        reach = (x**2 + y**2)**0.5
        if reach > 300:
            return False, f"XY reach too far: {reach:.1f}mm"
        
        if y < 100:
            return False, f"Y too close to base: {y}"
        
        return True, "OK"
    
    def emergency_stop(self, callback: Optional[Callable] = None):
        self._log("!!! EMERGENCY STOP !!!", callback)
        self._send_cmd("M112")
        self.controller.stop_requested = True
        self.controller.pause_requested = False
