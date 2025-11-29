"""
DexArm Controller - Core control class for DexArm robot arm
Handles serial communication and G-code commands
"""

import serial
import serial.tools.list_ports
import time
import json
import os
import threading
from pathlib import Path

CONFIG_FILE = Path(__file__).parent / "blade_positions.json"
BAUD_RATE = 115200


class DexArmController:
    def __init__(self):
        self.serial = None
        self.connected = False
        self.positions = self.load_positions()
        self.current_pos = {'x': 0, 'y': 300, 'z': 0}
        self.is_running = False
        self.pause_requested = False
        self.stop_requested = False
        
        # Timing settings (adjustable)
        self.settings = {
            'suction_grab_delay': 0.5,
            'suction_release_delay': 0.3,
            'feedrate': 3000,
        }
    
    @staticmethod
    def list_ports():
        """List available serial ports"""
        ports = serial.tools.list_ports.comports()
        return [port.device for port in ports]
    
    def connect(self, port):
        """Connect to DexArm"""
        try:
            self.serial = serial.Serial(port, BAUD_RATE, timeout=2)
            time.sleep(2)
            self.connected = True
            return True, "Connected successfully"
        except Exception as e:
            self.connected = False
            return False, str(e)
    
    def disconnect(self):
        """Disconnect from DexArm"""
        if self.serial:
            self.serial.close()
        self.connected = False
    
    def send_command(self, cmd, wait_ok=True):
        """Send G-code command and wait for 'ok'"""
        if not self.serial or not self.connected:
            return None
        
        try:
            self.serial.write(f"{cmd}\r".encode())
            if not wait_ok:
                self.serial.reset_input_buffer()
                return "sent"
            
            while True:
                response = self.serial.readline().decode().strip()
                if 'ok' in response.lower():
                    return response
                if not response:
                    time.sleep(0.05)
        except Exception as e:
            return f"Error: {e}"
    
    def go_home(self):
        """Move to home position"""
        self.send_command("M1112")
        time.sleep(2)
        self.current_pos = {'x': 0, 'y': 300, 'z': 0}
    
    def set_module(self, module_type):
        """Set front-end module (2 = Pneumatic)"""
        self.send_command(f"M888 P{module_type}")
        time.sleep(0.3)
    
    def move_to(self, x, y, z, feedrate=None):
        """Move to absolute position"""
        if feedrate is None:
            feedrate = self.settings['feedrate']
        cmd = f"G1 F{feedrate} X{x:.2f} Y{y:.2f} Z{z:.2f}"
        self.send_command(cmd)
        self.current_pos = {'x': x, 'y': y, 'z': z}
    
    def jog(self, axis, distance):
        """Jog relative movement on single axis"""
        self.send_command("G91")
        
        if axis == 'x':
            self.send_command(f"G1 F1000 X{distance}")
            self.current_pos['x'] += distance
        elif axis == 'y':
            self.send_command(f"G1 F1000 Y{distance}")
            self.current_pos['y'] += distance
        elif axis == 'z':
            self.send_command(f"G1 F1000 Z{distance}")
            self.current_pos['z'] += distance
        
        self.send_command("G90")
    
    def get_position(self):
        """Query current position from arm"""
        self.send_command("M114")
        try:
            response = self.serial.readline().decode().strip()
            parts = response.split()
            x = float(parts[0].split(':')[1])
            y = float(parts[1].split(':')[1])
            z = float(parts[2].split(':')[1])
            self.current_pos = {'x': x, 'y': y, 'z': z}
            return self.current_pos
        except:
            return self.current_pos
    
    def enable_teach_mode(self):
        """Disable motors for free movement"""
        self.send_command("M84")
        return True
    
    def disable_teach_mode(self):
        """Re-enable motors"""
        self.send_command("M17")
        return True
    
    def read_encoder_position(self):
        """Read magnet encoder position using M893"""
        while self.serial.in_waiting:
            self.serial.readline()
        time.sleep(0.1)
        
        self.serial.write(b"M893\n")
        time.sleep(0.5)
        
        for _ in range(20):
            try:
                if self.serial.in_waiting:
                    response = self.serial.readline().decode().strip()
                    if 'M894' in response or ('X' in response and 'Y' in response and 'Z' in response):
                        return response
                else:
                    time.sleep(0.1)
            except:
                pass
        return None
    
    def get_position_from_encoder(self):
        """Get actual position from encoder"""
        enc = self.read_encoder_position()
        if enc:
            try:
                enc = enc.replace("M894", "").strip()
                parts = enc.split()
                for part in parts:
                    if part.startswith('X'):
                        self.current_pos['x'] = float(part[1:])
                    elif part.startswith('Y'):
                        self.current_pos['y'] = float(part[1:])
                    elif part.startswith('Z'):
                        self.current_pos['z'] = float(part[1:])
            except Exception as e:
                print(f"Position parse error: {e}")
        return self.current_pos
    
    def move_to_encoder_position(self, encoder_string):
        """Move to a position using encoder values"""
        if encoder_string and ('X' in encoder_string or encoder_string.startswith('M894')):
            encoder_string = ' '.join(encoder_string.split())
            if not encoder_string.startswith('M894'):
                encoder_string = 'M894 ' + encoder_string
            self.send_command(encoder_string)
            self.send_command("M400")
            time.sleep(0.2)
            self.get_position()
            return True
        return False
    
    # === SUCTION CONTROL ===
    
    def suction_grab(self):
        """Activate suction"""
        self.send_command("M1000")
        time.sleep(self.settings['suction_grab_delay'])
    
    def suction_release(self):
        """Release suction"""
        self.send_command("M1002")
        time.sleep(self.settings['suction_release_delay'])
        self.send_command("M1003")
    
    def suction_off(self):
        """Turn off suction pump"""
        self.send_command("M1003")
    
    # === POSITION MANAGEMENT ===
    
    def load_positions(self):
        """Load saved positions from file"""
        default = {
            'pick': None,
            'safe_z': 0,
            'hooks': []
        }
        if CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE, 'r') as f:
                    return json.load(f)
            except:
                pass
        return default
    
    def save_positions(self):
        """Save positions to file"""
        with open(CONFIG_FILE, 'w') as f:
            json.dump(self.positions, f, indent=2)
    
    def set_pick(self):
        """Set current position as pick point"""
        self.get_position()
        encoder = self.read_encoder_position()
        self.positions['pick'] = {
            'x': self.current_pos['x'],
            'y': self.current_pos['y'],
            'z': self.current_pos['z'],
            'encoder': encoder
        }
        self.save_positions()
    
    def set_safe_z(self):
        """Set current Z as safe height"""
        self.get_position()
        self.positions['safe_z'] = self.current_pos['z']
        self.save_positions()
    
    def add_hook(self):
        """Add current position as a hook drop point"""
        self.get_position()
        encoder = self.read_encoder_position()
        self.positions['hooks'].append({
            'x': self.current_pos['x'],
            'y': self.current_pos['y'],
            'z': self.current_pos['z'],
            'encoder': encoder
        })
        self.save_positions()
        return len(self.positions['hooks']) - 1
    
    def delete_hook(self, index):
        """Delete a hook"""
        if 0 <= index < len(self.positions['hooks']):
            del self.positions['hooks'][index]
            self.save_positions()
    
    def clear_all_hooks(self):
        """Clear all hooks"""
        self.positions['hooks'] = []
        self.save_positions()
    
    def go_to_pick(self):
        """Move to pick position"""
        if self.positions.get('pick'):
            p = self.positions['pick']
            if p.get('encoder'):
                self.move_to_encoder_position(p['encoder'])
            else:
                self.move_to(p['x'], p['y'], p['z'])
    
    def go_to_hook(self, index):
        """Move to hook position"""
        if index < len(self.positions['hooks']):
            p = self.positions['hooks'][index]
            if p.get('encoder'):
                self.move_to_encoder_position(p['encoder'])
            else:
                self.move_to(p['x'], p['y'], p['z'])
    
    def go_to_safe_z(self):
        """Lift to safe Z height"""
        safe_z = self.positions.get('safe_z', 0)
        self.move_to(self.current_pos['x'], self.current_pos['y'], safe_z)
    
    # === CYCLE OPERATIONS ===
    
    def wait_for_move(self):
        """Wait for arm to finish moving"""
        self.send_command("M400")
    
    def pick_blade(self, callback=None):
        """Pick a blade"""
        pick = self.positions.get('pick')
        if not pick:
            return False
        
        safe_z = self.positions.get('safe_z', 0)
        f = self.settings['feedrate']
        
        if callback:
            callback("PICK")
        
        if callback:
            callback("  → Moving above pick")
        self.send_command(f"G1 F{f} X{pick['x']:.2f} Y{pick['y']:.2f} Z{safe_z:.2f}")
        self.wait_for_move()
        
        if callback:
            callback("  ✓ Suction ON")
        self.send_command("M1000")
        time.sleep(0.3)
        
        if callback:
            callback("  ↓ Lowering")
        self.send_command(f"G1 F{f} Z{pick['z']:.2f}")
        self.wait_for_move()
        
        time.sleep(self.settings['suction_grab_delay'])
        
        if callback:
            callback("  ↑ Lifting")
        self.send_command(f"G1 F{f} Z{safe_z:.2f}")
        self.wait_for_move()
        
        return True
    
    def place_blade(self, hook_index, callback=None):
        """Place blade on hook"""
        if hook_index >= len(self.positions['hooks']):
            return False
        
        hook = self.positions['hooks'][hook_index]
        safe_z = self.positions.get('safe_z', 0)
        f = self.settings['feedrate']
        
        if callback:
            callback(f"PLACE (Hook {hook_index})")
        
        if callback:
            callback("  → Moving above hook")
        self.send_command(f"G1 F{f} X{hook['x']:.2f} Y{hook['y']:.2f} Z{safe_z:.2f}")
        self.wait_for_move()
        
        if callback:
            callback("  ↓ Lowering")
        self.send_command(f"G1 F{f} Z{hook['z']:.2f}")
        self.wait_for_move()
        
        if callback:
            callback("  ✓ Release")
        self.send_command("M1002")
        time.sleep(0.5)
        self.send_command("M1003")
        time.sleep(0.2)
        
        if callback:
            callback("  ↑ Lifting")
        self.send_command(f"G1 F{f} Z{safe_z:.2f}")
        self.wait_for_move()
        
        return True
    
    def run_full_cycle(self, progress_callback=None, status_callback=None):
        """Run pick-and-place for all hooks"""
        self.is_running = True
        self.stop_requested = False
        self.pause_requested = False
        
        self.send_command("M2000")
        
        num_hooks = len(self.positions['hooks'])
        
        for i in range(num_hooks):
            if self.stop_requested:
                if status_callback:
                    status_callback("STOPPED")
                break
            
            while self.pause_requested:
                time.sleep(0.1)
                if self.stop_requested:
                    break
            
            if status_callback:
                status_callback(f"\n── Blade {i+1}/{num_hooks} ──")
            
            if not self.pick_blade(status_callback):
                break
            
            if not self.place_blade(i, status_callback):
                break
            
            if progress_callback:
                progress_callback(i + 1, num_hooks)
        
        self.suction_off()
        self.go_home()
        self.is_running = False
        
        if status_callback:
            status_callback("\n✓ DONE")
    
    def test_single_hook(self, hook_index, status_callback=None):
        """Test one hook"""
        self.is_running = True
        self.stop_requested = False
        
        if status_callback:
            status_callback(f"Testing hook {hook_index}")
        
        self.pick_blade(status_callback)
        self.place_blade(hook_index, status_callback)
        
        self.suction_off()
        self.is_running = False
        
        if status_callback:
            status_callback("Done")
    
    def pause_cycle(self):
        self.pause_requested = True
    
    def resume_cycle(self):
        self.pause_requested = False
    
    def stop_cycle(self):
        self.stop_requested = True
        self.pause_requested = False
