"use client";

import useSWR from "swr";
import { fetcher } from "@/lib/fetcher";

export interface CreatorParam {
  name: string;
  type: string;
  default: unknown;
  required: boolean;
  description: string | null;
}

export interface CreatorInfo {
  class_name: string;
  category: string;
  description: string | null;
  parameters: CreatorParam[];
}

export const CREATOR_CATEGORIES = [
  "wing",
  "fuselage",
  "cad_operations",
  "export_import",
  "components",
] as const;

export type CreatorCategory = (typeof CREATOR_CATEGORIES)[number];

export function useCreators() {
  const { data, error, isLoading } = useSWR<CreatorInfo[]>(
    "/construction-plans/creators",
    fetcher,
  );

  return {
    creators: data ?? [],
    error,
    isLoading,
  };
}
