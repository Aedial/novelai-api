const fflate = require("fflate")

input = process.argv[2];
result = fflate.strFromU8(fflate.inflateSync(Buffer.from(input, "base64")))
console.log(result);