const http = require("http");
const { invoiceTotal } = require("./invoice");

http
  .createServer((req, res) => {
    if (req.method === "POST" && req.url === "/invoice/total") {
      let body = "";
      req.on("data", (c) => (body += c));
      req.on("end", () => {
        const total = invoiceTotal(JSON.parse(body).lines);
        res.setHeader("content-type", "application/json");
        res.end(JSON.stringify({ totalCents: total }));
      });
      return;
    }
    res.statusCode = 404;
    res.end();
  })
  .listen(process.env.PORT || 3000);
