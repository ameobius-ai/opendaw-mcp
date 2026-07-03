#!/usr/bin/env python3
"""Simple standard MIDI file parser — extracts note events.
No external dependencies. Supports format 0 and 1.
Returns list of notes: (pitch, start_tick, duration_ticks, velocity, channel).
"""
import struct
from typing import List, Tuple

class MidiNote:
    __slots__ = ('pitch', 'start_tick', 'duration_ticks', 'velocity', 'channel')
    def __init__(self, pitch, start_tick, duration_ticks, velocity, channel):
        self.pitch = pitch
        self.start_tick = start_tick
        self.duration_ticks = duration_ticks
        self.velocity = velocity
        self.channel = channel
    def __repr__(self):
        return f"Note(pitch={self.pitch}, start={self.start_tick}, dur={self.duration_ticks}, vel={self.velocity}, ch={self.channel})"


def read_varlen(data: bytes, pos: int) -> Tuple[int, int]:
    """Read variable-length quantity. Returns (value, new_pos)."""
    value = data[pos] & 0x7f
    pos += 1
    while data[pos - 1] & 0x80:
        value = (value << 7) | (data[pos] & 0x7f)
        pos += 1
    return value, pos


def parse_midi_file(data: bytes) -> List[MidiNote]:
    """Parse standard MIDI file and return list of notes.
    
    Converts MIDI ticks to openDAW PPQN (960 ticks per quarter note).
    """
    pos = 0
    
    # Read header chunk
    if data[0:4] != b'MThd':
        raise ValueError("Not a MIDI file (no MThd header)")
    header_len = struct.unpack('>I', data[4:8])[0]
    format_type = struct.unpack('>H', data[8:10])[0]
    num_tracks = struct.unpack('>H', data[10:12])[0]
    time_division = struct.unpack('>H', data[12:14])[0]
    
    # PPQN (pulses per quarter note) — usually 480, sometimes 96, 384, 960
    ppqn = time_division if time_division < 0x8000 else 0  # SMPTE not supported
    
    pos = 8 + header_len
    
    all_notes = []
    
    for track_idx in range(num_tracks):
        if pos + 8 > len(data):
            break
        
        chunk_id = data[pos:pos+4]
        chunk_len = struct.unpack('>I', data[pos+4:pos+8])[0]
        pos += 8
        
        if chunk_id != b'MTrk':
            pos += chunk_len
            continue
        
        track_end = pos + chunk_len
        track_data = data[pos:track_end]
        track_pos = 0
        
        # Parse events
        tick = 0
        active_notes = {}  # (channel, pitch) -> (start_tick, velocity)
        running_status = 0
        
        while track_pos < len(track_data):
            # Delta time
            delta, track_pos = read_varlen(track_data, track_pos)
            tick += delta
            
            if track_pos >= len(track_data):
                break
            
            status_byte = track_data[track_pos]
            
            # Handle running status
            if status_byte < 0x80:
                # Use running status
                if running_status == 0:
                    track_pos += 1
                    continue
                status_byte = running_status
            else:
                track_pos += 1
                running_status = status_byte
            
            msg_type = status_byte & 0xf0
            channel = status_byte & 0x0f
            
            if msg_type == 0x80:  # Note Off
                pitch = track_data[track_pos]
                track_pos += 2  # pitch + velocity
                key = (channel, pitch)
                if key in active_notes:
                    start_tick, velocity = active_notes.pop(key)
                    dur = tick - start_tick
                    all_notes.append(MidiNote(pitch, start_tick, dur, velocity, channel))
            
            elif msg_type == 0x90:  # Note On
                pitch = track_data[track_pos]
                velocity = track_data[track_pos + 1]
                track_pos += 2
                if velocity == 0:
                    # Note on with velocity 0 = note off
                    key = (channel, pitch)
                    if key in active_notes:
                        start_tick, vel = active_notes.pop(key)
                        dur = tick - start_tick
                        all_notes.append(MidiNote(pitch, start_tick, dur, vel, channel))
                else:
                    active_notes[(channel, pitch)] = (tick, velocity / 127.0)
            
            elif msg_type == 0xA0:  # Polyphonic Pressure
                track_pos += 2
            elif msg_type == 0xB0:  # Control Change
                track_pos += 2
            elif msg_type == 0xC0:  # Program Change
                track_pos += 1
            elif msg_type == 0xD0:  # Channel Pressure
                track_pos += 1
            elif msg_type == 0xE0:  # Pitch Bend
                track_pos += 2
            elif status_byte == 0xFF:  # Meta event
                meta_type = track_data[track_pos]
                track_pos += 1
                meta_len, track_pos = read_varlen(track_data, track_pos)
                if meta_type == 0x51:  # Tempo
                    pass  # Could parse tempo but we just need ticks
                track_pos += meta_len
            elif status_byte == 0xF0:  # SysEx
                sysex_len, track_pos = read_varlen(track_data, track_pos)
                track_pos += sysex_len
            elif status_byte == 0xF7:  # SysEx escape
                sysex_len, track_pos = read_varlen(track_data, track_pos)
                track_pos += sysex_len
            else:
                # Unknown — skip 1 byte to avoid infinite loop
                pass
        
        pos = track_end
    
    # Convert ticks from source PPQN to openDAW PPQN (960)
    if ppqn > 0 and ppqn != 960:
        scale = 960.0 / ppqn
        for note in all_notes:
            note.start_tick = int(note.start_tick * scale)
            note.duration_ticks = int(note.duration_ticks * scale)
    
    # Sort by start tick
    all_notes.sort(key=lambda n: n.start_tick)
    
    return all_notes, ppqn


def ticks_to_beats(ticks: int) -> float:
    """Convert openDAW ticks (PPQN=960) to beats."""
    return ticks / 960.0


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python3 midi_parser.py <file.mid>")
        sys.exit(1)
    with open(sys.argv[1], 'rb') as f:
        data = f.read()
    notes, ppqn = parse_midi_file(data)
    print(f"PPQN: {ppqn}, Notes: {len(notes)}")
    for n in notes[:20]:
        beat = ticks_to_beats(n.start_tick)
        dur_beat = ticks_to_beats(n.duration_ticks)
        print(f"  pitch={n.pitch} start={beat:.2f}b dur={dur_beat:.2f}b vel={n.velocity:.2f} ch={n.channel}")
    if len(notes) > 20:
        print(f"  ... and {len(notes) - 20} more")
