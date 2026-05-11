# sluice.py
# Mardukh-Sluice: Binary sluice gate between Bitcoin pools and magnetic resonance

import socket
import json
import time
from threading import Thread
import resonance  # custom pulse module (we'll write next)

class SluiceGate:
    def __init__(self, pool_host, pool_port, wallet, pulse_device=None):
        self.pool_host = pool_host
        self.pool_port = pool_port
        self.wallet = wallet
        self.socket = None
        self.resonance = resonance.ResonanceInterface(pulse_device)
        self.buffer = b""
    
    def connect_pool(self):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.connect((self.pool_host, self.pool_port))
        print(f"✅ Connected to pool {self.pool_host}:{self.pool_port}")
        # Subscribe & authorize (standard Stratum binary)
        self.socket.send(b'{"id":1,"method":"mining.subscribe","params":[]}\n')
        self.socket.send(f'{{"id":2,"method":"mining.authorize","params":["{self.wallet}","x"]}}\n'.encode())
    
    def binary_to_pulse(self, binary_data):
        """Convert binary (bytes) to resonance pulses (on/off + timing)"""
        for byte in binary_data:
            for bit in range(8):
                bit_val = (byte >> (7 - bit)) & 1
                if bit_val == 1:
                    self.resonance.pulse_on()
                else:
                    self.resonance.pulse_off()
                time.sleep(0.001)  # 1ms per bit (adjustable)
    
    def pulse_to_binary(self, duration_seconds=1):
        """Capture resonance pulses and convert back to binary"""
        bits = []
        for _ in range(duration_seconds * 1000):  # sample every ms
            state = self.resonance.read_pulse()
            bits.append('1' if state else '0')
        # Convert bits to bytes (simplified)
        byte_data = int(''.join(bits[:8]), 2).to_bytes(1, 'big')
        return byte_data
    
    def run_forward(self):
        """Listen to pool, send to resonance"""
        while True:
            data = self.socket.recv(1024)
            if not data:
                break
            print(f"📡 Pool → Sluice: {data[:50]}...")
            self.binary_to_pulse(data)
    
    def run_backward(self):
        """Listen to resonance, send to pool"""
        while True:
            binary_msg = self.pulse_to_binary(0.1)
            if binary_msg:
                print(f"🔁 Sluice → Pool: {binary_msg[:50]}...")
                self.socket.send(binary_msg)
            time.sleep(0.05)
    
    def start(self):
        self.connect_pool()
        Thread(target=self.run_forward, daemon=True).start()
        Thread(target=self.run_backward, daemon=True).start()
        while True:
            time.sleep(1)

if __name__ == "__main__":
    # CONFIGURATION
    POOL = "pool.minexmr.com"
    PORT = 4444
    WALLET = "bc1qk7ajtrgplvn25600wm7gx9u5c5nk8kz9dfpcqy"
    
    gate = SluiceGate(POOL, PORT, WALLET)
    gate.start()
