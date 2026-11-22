// Offline recoder: observe each decoded v2 bit and write the same symbol with
// its original probability, except inside the candidate's int4 tensors.
#include <algorithm>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <vector>

namespace trial {
struct Encoder {
  uint64_t low = 0;
  uint32_t range = ~uint32_t(0);
  unsigned cache = 0, pending = 1;
  std::vector<uint8_t> bytes;
  void shift() {
    if (low < 0xff000000ULL || (low >> 32)) {
      unsigned carry = unsigned(low >> 32);
      bytes.push_back(uint8_t(cache + carry));
      while (--pending) bytes.push_back(uint8_t(255 + carry));
      cache = unsigned(low >> 24) & 255;
    }
    ++pending;
    low = uint32_t(low << 8);
  }
  void bit(unsigned p, unsigned b) {
    uint32_t bound = (range >> 11) * p;
    if (b) { low += bound; range -= bound; }
    else range = bound;
    while (range < (1u << 24)) { range <<= 8; shift(); }
  }
};
inline Encoder enc;
inline bool change = false, in_weights = false;
inline std::vector<uint8_t> tables;
inline size_t symbols = 0;
inline void observed(unsigned p, unsigned b) {
  if (!(change && in_weights)) enc.bit(p, b);
}
inline void emit_tensor(const int8_t* data, size_t n) {
  symbols += n;
  if (!change) return;
  uint64_t counts[32]{};
  for (size_t i = 0; i < n; ++i) {
    int s = data[i] + 7;
    if (s < 0 || s >= 15) std::abort();
    ++counts[16+s];
  }
  for (int k = 15; k > 0; --k) counts[k] = counts[2*k] + counts[2*k+1];
  unsigned p[15]{};
  for (int k = 1; k < 15; ++k) {
    p[k] = counts[k] ? unsigned((2048*counts[2*k] + counts[k]/2)/counts[k]) : 1024;
    p[k] = std::clamp(p[k], 1u, 2047u);
    tables.push_back(uint8_t(p[k])); tables.push_back(uint8_t(p[k] >> 8));
  }
  for (size_t i = 0; i < n; ++i) {
    unsigned node = 1, s = unsigned(data[i]+7);
    for (int k = 3; k >= 0; --k) {
      unsigned b = (s >> k) & 1u;
      if (node != 15) enc.bit(p[node], b);
      node = 2*node+b;
    }
  }
}
}  // namespace trial
