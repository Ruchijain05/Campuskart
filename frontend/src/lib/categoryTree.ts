import type { Category, CategoryTree } from "./types";

export interface CategoryOption {
  category: Category;
  depth: number;
  path: string;
}

export function buildCategoryTree(categories: Category[]): CategoryTree[] {
  const nodes = new Map<number, CategoryTree>();
  for (const category of categories) {
    nodes.set(category.id, { ...category, children: [] });
  }

  const roots: CategoryTree[] = [];
  for (const category of categories) {
    const node = nodes.get(category.id);
    if (!node) continue;
    const parent = category.parent_id === null ? undefined : nodes.get(category.parent_id);
    if (parent) parent.children.push(node);
    else roots.push(node);
  }

  const sortTree = (items: CategoryTree[]) => {
    items.sort((left, right) => left.name.localeCompare(right.name));
    for (const item of items) sortTree(item.children);
  };
  sortTree(roots);
  return roots;
}

export function flattenCategoryTree(
  categories: CategoryTree[],
  depth = 0,
  parents: string[] = [],
): CategoryOption[] {
  return categories.flatMap((category) => {
    const path = [...parents, category.name];
    return [
      { category, depth, path: path.join(" / ") },
      ...flattenCategoryTree(category.children, depth + 1, path),
    ];
  });
}

export function getCategoryDescendantIds(
  categories: Category[],
  categoryId: number,
): Set<number> {
  const descendants = new Set<number>([categoryId]);
  const pending = [categoryId];
  while (pending.length) {
    const parentId = pending.pop();
    for (const category of categories) {
      if (category.parent_id === parentId && !descendants.has(category.id)) {
        descendants.add(category.id);
        pending.push(category.id);
      }
    }
  }
  return descendants;
}
