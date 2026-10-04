export async function callUpstream(send: () => Promise<Response>): Promise<Response> {
  for (let attempt = 0; attempt < 3; attempt++) {
    const res = await send();
    if (res.ok) return res;
  }
  throw new Error("upstream failed");
}
