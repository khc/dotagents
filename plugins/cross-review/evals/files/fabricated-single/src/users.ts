export function findUser(db: Db, id: number) {
  return db.query("SELECT * FROM users WHERE id = $1", [id]);
}
