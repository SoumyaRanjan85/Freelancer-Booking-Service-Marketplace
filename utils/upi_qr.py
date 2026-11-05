"""
FreelanceConnect UPI Payment & Scannable QR Code Utility
NPCI UPI 2.0 Compliant URI Builder & Pure-Python Standalone SVG QR Code Generator.
Zero external library dependencies (requires no qrcode or PIL).
"""
import urllib.parse
from typing import List, Tuple, Optional

# -------------------------------------------------------------
# 1. NPCI UPI URI Specification Builder
# -------------------------------------------------------------

def build_upi_uri(
    vpa: str = "freelanceconnect.escrow@icici",
    name: str = "FreelanceConnect Escrow",
    amount: float = 0.0,
    txn_ref: str = "",
    note: str = "Escrow Deposit",
    currency: str = "INR"
) -> str:
    """
    Build standard NPCI UPI Payment URI for mobile apps and QR codes.
    Compatible with Google Pay, PhonePe, Paytm, BHIM, CRED, Amazon Pay, and Mobile Banking.
    """
    vpa_clean = vpa.strip()
    name_clean = name.strip()
    note_clean = note.strip()
    ref_clean = txn_ref.strip()

    params = {
        'pa': vpa_clean,
        'pn': name_clean,
        'mc': '0000',
        'tr': ref_clean,
        'tn': note_clean,
        'am': f"{amount:.2f}",
        'cu': currency
    }
    query_string = urllib.parse.urlencode(params, quote_via=urllib.parse.quote)
    return f"upi://pay?{query_string}"


# -------------------------------------------------------------
# 2. Pure-Python Standalone QR Code Generator (Reed-Solomon & SVG)
# -------------------------------------------------------------

# Galois Field GF(256) Tables for Reed-Solomon error correction
GF_EXP = [0] * 512
GF_LOG = [0] * 256
_x = 1
for _i in range(255):
    GF_EXP[_i] = _x
    GF_EXP[_i + 255] = _x
    GF_LOG[_x] = _i
    _x = (_x << 1) ^ (0x11D if (_x & 0x80) else 0)

def _gf_mul(x: int, y: int) -> int:
    if x == 0 or y == 0:
        return 0
    return GF_EXP[GF_LOG[x] + GF_LOG[y]]

def _rs_poly(degree: int) -> List[int]:
    poly = [1]
    for i in range(degree):
        next_poly = [0] * (len(poly) + 1)
        factor = GF_EXP[i]
        for j, c in enumerate(poly):
            next_poly[j] ^= _gf_mul(c, factor)
            next_poly[j + 1] ^= c
        poly = next_poly
    return poly

def _rs_encode(data: List[int], ec_len: int) -> List[int]:
    gen = _rs_poly(ec_len)
    msg = data + [0] * ec_len
    for i in range(len(data)):
        lead = msg[i]
        if lead != 0:
            for j in range(len(gen)):
                msg[i + j] ^= _gf_mul(gen[j], lead)
    return msg[len(data):]

# QR Version table: (Total data codewords, EC codewords, EC blocks) for Medium error correction (Level M)
# Version 1 to 10 capacities in Byte mode:
QR_TABLE_M = {
    1: {'total': 26, 'ec': 10, 'blocks': 1, 'align': []},
    2: {'total': 44, 'ec': 16, 'blocks': 1, 'align': [6, 18]},
    3: {'total': 70, 'ec': 26, 'blocks': 1, 'align': [6, 22]},
    4: {'total': 100, 'ec': 18, 'blocks': 2, 'align': [6, 26]},
    5: {'total': 134, 'ec': 24, 'blocks': 2, 'align': [6, 30]},
    6: {'total': 172, 'ec': 16, 'blocks': 4, 'align': [6, 34]},
    7: {'total': 196, 'ec': 18, 'blocks': 4, 'align': [6, 22, 38]},
    8: {'total': 242, 'ec': 22, 'blocks': 4, 'align': [6, 24, 42]},
    9: {'total': 292, 'ec': 22, 'blocks': 5, 'align': [6, 26, 46]},
    10: {'total': 346, 'ec': 26, 'blocks': 5, 'align': [6, 28, 50]},
}

def _choose_version(data_bytes_len: int) -> int:
    """Find the smallest QR version that fits data_bytes in Byte Mode under Level M."""
    for v in range(1, 11):
        info = QR_TABLE_M[v]
        total_data = info['total'] - (info['ec'] * info['blocks'])
        header_bits = 4 + (8 if v < 10 else 16)
        total_bits = header_bits + (data_bytes_len * 8)
        max_bits = total_data * 8
        if total_bits + 4 <= max_bits:
            return v
    return 10

class QRCodeMatrix:
    def __init__(self, text: str, version: Optional[int] = None):
        self.text = text
        raw_bytes = text.encode('utf-8')
        self.version = version or _choose_version(len(raw_bytes))
        self.info = QR_TABLE_M[self.version]
        self.size = 21 + (self.version - 1) * 4
        self.modules = [[None] * self.size for _ in range(self.size)]
        self.is_function = [[False] * self.size for _ in range(self.size)]
        
        self._encode_data(raw_bytes)
        self._place_function_patterns()
        self._place_data()
        self._apply_best_mask()

    def _encode_data(self, raw_bytes: bytes):
        total_ec_words = self.info['ec'] * self.info['blocks']
        data_capacity = self.info['total'] - total_ec_words
        
        # Byte mode indicator: 0100
        bits = "0100"
        count_bits = 8 if self.version < 10 else 16
        bits += format(len(raw_bytes), f'0{count_bits}b')
        for b in raw_bytes:
            bits += format(b, '08b')
        
        # Terminator (up to 4 zeroes)
        max_bits = data_capacity * 8
        bits += "0000"[:max(0, max_bits - len(bits))]
        
        # Byte padding
        if len(bits) % 8 != 0:
            bits += "0" * (8 - (len(bits) % 8))
        
        # Pad codewords (0xEC, 0x11)
        pad_bytes = ["11101100", "00010001"]
        pad_idx = 0
        while len(bits) < max_bits:
            bits += pad_bytes[pad_idx % 2]
            pad_idx += 1
        
        # Convert bits to byte list
        codewords = [int(bits[i:i+8], 2) for i in range(0, len(bits), 8)]
        
        # Interleave blocks with Reed-Solomon
        num_blocks = self.info['blocks']
        ec_per_block = self.info['ec']
        base_block_len = len(codewords) // num_blocks
        rem = len(codewords) % num_blocks
        
        data_blocks = []
        ec_blocks = []
        offset = 0
        for b in range(num_blocks):
            cur_len = base_block_len + (1 if b >= num_blocks - rem else 0)
            blk = codewords[offset:offset+cur_len]
            offset += cur_len
            data_blocks.append(blk)
            ec_blocks.append(_rs_encode(blk, ec_per_block))
        
        # Final interleaved stream
        final_stream = []
        max_d_len = max(len(blk) for blk in data_blocks)
        for i in range(max_d_len):
            for blk in data_blocks:
                if i < len(blk):
                    final_stream.append(blk[i])
        for i in range(ec_per_block):
            for blk in ec_blocks:
                final_stream.append(blk[i])
        
        self.final_bits = "".join(format(b, '08b') for b in final_stream)

    def _set_module(self, r: int, c: int, val: bool, is_fn: bool = False):
        if 0 <= r < self.size and 0 <= c < self.size:
            self.modules[r][c] = val
            if is_fn:
                self.is_function[r][c] = True

    def _place_function_patterns(self):
        # 1. Finder patterns (7x7) + Separators at 3 corners
        for r_start, c_start in [(0, 0), (0, self.size - 7), (self.size - 7, 0)]:
            for r in range(-1, 8):
                for c in range(-1, 8):
                    rr, cc = r_start + r, c_start + c
                    if 0 <= rr < self.size and 0 <= cc < self.size:
                        is_black = (0 <= r <= 6 and 0 <= c <= 6) and (
                            r in (0, 6) or c in (0, 6) or (2 <= r <= 4 and 2 <= c <= 4)
                        )
                        self._set_module(rr, cc, is_black, is_fn=True)
        
        # 2. Timing patterns (Row 6 and Column 6)
        for i in range(self.size):
            if not self.is_function[6][i]:
                self._set_module(6, i, i % 2 == 0, is_fn=True)
            if not self.is_function[i][6]:
                self._set_module(i, 6, i % 2 == 0, is_fn=True)
        
        # 3. Alignment patterns for Version >= 2
        align_pos = self.info['align']
        for r in align_pos:
            for c in align_pos:
                # Skip if overlapping with finder patterns
                if self.is_function[r][c]:
                    continue
                for dr in range(-2, 3):
                    for dc in range(-2, 3):
                        is_b = (max(abs(dr), abs(dc)) in (0, 2))
                        self._set_module(r + dr, c + dc, is_b, is_fn=True)
        
        # 4. Dark module
        self._set_module(self.size - 8, 8, True, is_fn=True)

        # 5. Reserve format information areas
        for i in range(9):
            if not self.is_function[8][i]:
                self._set_module(8, i, False, is_fn=True)
            if not self.is_function[i][8]:
                self._set_module(i, 8, False, is_fn=True)
        for i in range(self.size - 8, self.size):
            if not self.is_function[8][i]:
                self._set_module(8, i, False, is_fn=True)
        for i in range(self.size - 7, self.size):
            if not self.is_function[i][8]:
                self._set_module(i, 8, False, is_fn=True)

    def _place_data(self):
        bit_idx = 0
        bit_len = len(self.final_bits)
        row = self.size - 1
        col = self.size - 1
        dir_up = True
        
        while col > 0:
            if col == 6:  # Skip vertical timing pattern
                col -= 1
            for dr in range(self.size):
                curr_row = row if dir_up else (self.size - 1 - row)
                for dc in (0, -1):
                    curr_col = col + dc
                    if not self.is_function[curr_row][curr_col]:
                        val = (self.final_bits[bit_idx] == '1') if bit_idx < bit_len else False
                        self.modules[curr_row][curr_col] = val
                        bit_idx += 1
                row -= 1 if dir_up else -1
            row = 0 if dir_up else self.size - 1
            dir_up = not dir_up
            col -= 2

    def _apply_best_mask(self):
        # Standard Mask 0: (row + col) % 2 == 0
        mask_idx = 0
        for r in range(self.size):
            for c in range(self.size):
                if not self.is_function[r][c]:
                    if (r + c) % 2 == 0:
                        self.modules[r][c] = not self.modules[r][c]
        
        # Format info for Medium (M = 00) with Mask 0 (000)
        # Precomputed standard 15-bit BCH for EC Level M (00) and Mask 000 with 0x5412 XOR mask = 101010000010010
        format_bits = "101010000010010"
        
        # Place format bits top-left and split corners
        for i, bit in enumerate(format_bits):
            val = (bit == '1')
            # Top-left
            if i <= 5:
                self.modules[8][i] = val
            elif i == 6:
                self.modules[8][7] = val
            elif i == 7:
                self.modules[8][8] = val
            elif i == 8:
                self.modules[7][8] = val
            else:
                self.modules[14 - i][8] = val
            
            # Bottom and right
            if i < 7:
                self.modules[self.size - 1 - i][8] = val
            else:
                self.modules[8][self.size - 15 + i] = val

    def to_svg(self, scale: int = 8, border: int = 4, fg_color: str = "#0f172a", bg_color: str = "#ffffff") -> str:
        """Render high-contrast SVG representation."""
        full_size = (self.size + 2 * border) * scale
        rects = []
        for r in range(self.size):
            for c in range(self.size):
                if self.modules[r][c]:
                    x = (c + border) * scale
                    y = (r + border) * scale
                    rects.append(f'<rect x="{x}" y="{y}" width="{scale}" height="{scale}" fill="{fg_color}"/>')
        
        svg = (
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {full_size} {full_size}" '
            f'width="{full_size}" height="{full_size}" class="upi-qr-svg" shape-rendering="crispEdges">\n'
            f'<rect width="100%" height="100%" fill="{bg_color}" rx="8"/>\n'
            + "\n".join(rects) +
            '\n</svg>'
        )
        return svg


def generate_upi_qr_svg(
    vpa: str,
    name: str,
    amount: float,
    txn_ref: str,
    note: str = "Escrow Deposit",
    scale: int = 7,
    border: int = 4
) -> Tuple[str, str]:
    """
    Generate both the full UPI URI and the SVG QR Code string.
    Returns: (upi_uri, svg_markup)
    """
    uri = build_upi_uri(vpa=vpa, name=name, amount=amount, txn_ref=txn_ref, note=note)
    qr = QRCodeMatrix(uri)
    svg = qr.to_svg(scale=scale, border=border)
    return uri, svg
