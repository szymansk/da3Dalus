export function displaySurfaceName(encoded: string): string {
  const match = encoded.match(/^\[(\w+)\](.+)$/);
  return match ? match[2] : encoded;
}
