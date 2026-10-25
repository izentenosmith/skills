import http from "k6/http";
import { check } from "k6";

export const options = { vus: 20, duration: "1m" };

export default function () {
  const r = http.get(`${__ENV.BASE_URL}/invoices/INV-1`);
  check(r, { "200": (res) => res.status === 200 });
}
