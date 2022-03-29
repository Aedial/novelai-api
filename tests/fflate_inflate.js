const fflate = require("fflate")

let input_len = parseInt(process.argv[2]);
let i = 0;
let buffers = []

// chunk size for writing
// choosing a value too high seems to sometimes crop the output in a non deterministic way
const stdout_limit = 512;

process.stdin.on("data", data => {
    if (data != null)
    {
        i += data.length;
        buffers.push(data);
    }

    if (i == input_len)
    {
        buf = Buffer.concat(buffers);
        result = fflate.inflateSync(buf);

        do {
            const size = Math.min(result.length, stdout_limit);
            process.stdout.write(result.subarray(0, size));

            result = result.subarray(size);
        } while (result.length != 0);

        process.exit();
    }
});

