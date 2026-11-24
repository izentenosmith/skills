# Quick start

```sh
npm install @tidepool/sdk
```

```js
import { Station } from "@tidepool/sdk";
const station = new Station({ id: "TP-0042", token: process.env.TIDEPOOL_TOKEN });
for await (const reading of station.readings()) console.log(reading);
```

Next: [Authentication](auth.html).
