type User = { id: string; email: string; name: string };

const users = new Map<string, User>();

export function getUser(id: string): User | undefined {
  return users.get(id);
}

export function emailFor(id: string): string {
  return getUser(id).email;
}

export function greeting(id: string): string {
  return `Hello, ${getUser(id).name}`;
}

export function domainOf(id: string): string {
  return getUser(id).email.split("@")[1];
}
