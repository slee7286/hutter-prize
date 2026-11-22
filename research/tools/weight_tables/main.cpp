// Two targets: offline recoding (RECODE) and an identically built tensor dumper.
#include "weights_io.h"
#include <algorithm>
#include <cstdio>
#include <cstring>
#ifdef RECODE
#include "transcode.hpp"
#endif

static void write_bytes(const void *p, size_t n) {
  if (n && std::fwrite(p, 1, n, stdout) != n) std::exit(2);
}
static void u32(uint32_t n) { write_bytes(&n, 4); } // x86-64 little endian
int main(int argc, char** argv) {
#ifdef RECODE
  if (argc != 3) return 2;
  trial::change = !std::strcmp(argv[2], "tables");
#else
  if (argc != 2) return 2;
#endif
  auto wf = fx2::WeightsFile::load_compressed(argv[1]);
#ifdef RECODE
  for (int i = 0; i < 5; ++i) trial::enc.shift();
  write_bytes(trial::change ? "FX2TFT01" : "FX2TFWC2", 8);
  u32(wf.tensors.size());
  if (trial::change) {
    u32(trial::tables.size());
    write_bytes(trial::tables.data(), trial::tables.size());
  }
  write_bytes(trial::enc.bytes.data(), trial::enc.bytes.size());
  std::fprintf(stderr, "%zu %zu %zu\n", wf.tensors.size(), trial::tables.size(), trial::symbols);
#else
  std::vector<std::string> keys;
  for (const auto& entry : wf.tensors) keys.push_back(entry.first);
  std::sort(keys.begin(), keys.end());
  u32(wf.tensors.size());
  for (const auto& key : keys) {
    const auto& t = wf.get(key);
    u32(key.size()); write_bytes(key.data(), key.size()); write_bytes(&t.dtype, 1);
    u32(t.shape.size()); write_bytes(t.shape.data(), 4*t.shape.size());
    u32(t.data.size()); write_bytes(t.data.data(), t.data.size());
  }
#endif
  return std::fflush(stdout) ? 2 : 0;
}
