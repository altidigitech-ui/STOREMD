export const ADMIN_EMAIL = "altidigitech@gmail.com";

export function isAdmin(email: string | null | undefined): boolean {
  return (email ?? "").toLowerCase() === ADMIN_EMAIL;
}
