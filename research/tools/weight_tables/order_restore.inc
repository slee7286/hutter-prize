// Decode the two planes of uint16 run labels into the original decimal order.
// Zero means missing ID. Prepending increasing IDs orders each run descending.
static void RestoreArticleOrder() {
  FILE *f = fopen(".order_labels", "rb");
  if (!f || fseek(f, 0, SEEK_END)) exit(EXIT_FAILURE);
  long bytes = ftell(f);
  if (bytes <= 0 || bytes % 2 || bytes > 2 * 1000000) exit(EXIT_FAILURE);
  rewind(f);
  int n = int(bytes / 2);
  std::vector<unsigned char> planes(bytes);
  if (fread(planes.data(), 1, bytes, f) != size_t(bytes)) exit(EXIT_FAILURE);
  fclose(f);
  std::vector<int> head(65536, -1), next(n);
  for (int i = 0; i < n; ++i) {
    unsigned run = planes[i] + 256u * planes[n+i];
    if (run) { next[i] = head[run]; head[run] = i; }
  }
  f = fopen(".new_article_order", "wb");
  if (!f) exit(EXIT_FAILURE);
  for (unsigned run = 1; run < head.size(); ++run)
    for (int i = head[run]; i >= 0; i = next[i])
      if (fprintf(f, "%d\n", i) < 0) exit(EXIT_FAILURE);
  if (fclose(f)) exit(EXIT_FAILURE);
}
