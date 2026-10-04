import { parseLegacyId } from "./utils";

export function migrateRecord(raw: string): number {
  return parseLegacyId(raw);
}
