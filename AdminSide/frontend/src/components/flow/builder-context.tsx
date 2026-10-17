"use client";

import { createContext, useContext } from "react";

export interface BuilderHandlers {
  onEdit: (id: string) => void;
  onDuplicate: (id: string) => void;
  onDelete: (id: string) => void;
  selectedId: string | null;
}

export const BuilderContext = createContext<BuilderHandlers>({
  onEdit: () => {},
  onDuplicate: () => {},
  onDelete: () => {},
  selectedId: null,
});

export const useBuilder = () => useContext(BuilderContext);
