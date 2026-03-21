const MOJIBAKE_LATIN_RE = /[ÃÐÑ]|â€”|â€“|â€|â„|â€™/;
const MOJIBAKE_CP1251_RE = /[€‚ƒ„…†‡ˆ‰Š‹ŒŽ‘’“”•–—˜™š›œžŸ°±²³µ¶·¸¹º»¼½¾¿]/;
const MOJIBAKE_RU_RE = /[ЂЃЉЊЋЌЍЎЏЇЄҐђѓљњћќўїєґ]/;
const RUS_LETTER_RE = /[А-Яа-яЁё]/g;
const LATIN_LETTER_RE = /[A-Za-z]/g;
const WEIRD_CYRILLIC_RE = /[ЂЃЉЊЋЌЍЎЏЇЄҐђѓљњћќўїєґ]/g;
const CP1251_TABLE = [
    0x0402, 0x0403, 0x201a, 0x0453, 0x201e, 0x2026, 0x2020, 0x2021,
    0x20ac, 0x2030, 0x0409, 0x2039, 0x040a, 0x040c, 0x040b, 0x040f,
    0x0452, 0x2018, 0x2019, 0x201c, 0x201d, 0x2022, 0x2013, 0x2014,
    0x02dc, 0x2122, 0x0459, 0x203a, 0x045a, 0x045c, 0x045b, 0x045f,
    0x00a0, 0x040e, 0x045e, 0x0408, 0x00a4, 0x0490, 0x00a6, 0x00a7,
    0x0401, 0x00a9, 0x0404, 0x00ab, 0x00ac, 0x00ad, 0x00ae, 0x0407,
    0x00b0, 0x00b1, 0x0406, 0x0456, 0x0491, 0x00b5, 0x00b6, 0x00b7,
    0x0451, 0x2116, 0x0454, 0x00bb, 0x0458, 0x0405, 0x0455, 0x0457,
    0x0410, 0x0411, 0x0412, 0x0413, 0x0414, 0x0415, 0x0416, 0x0417,
    0x0418, 0x0419, 0x041a, 0x041b, 0x041c, 0x041d, 0x041e, 0x041f,
    0x0420, 0x0421, 0x0422, 0x0423, 0x0424, 0x0425, 0x0426, 0x0427,
    0x0428, 0x0429, 0x042a, 0x042b, 0x042c, 0x042d, 0x042e, 0x042f,
    0x0430, 0x0431, 0x0432, 0x0433, 0x0434, 0x0435, 0x0436, 0x0437,
    0x0438, 0x0439, 0x043a, 0x043b, 0x043c, 0x043d, 0x043e, 0x043f,
    0x0440, 0x0441, 0x0442, 0x0443, 0x0444, 0x0445, 0x0446, 0x0447,
    0x0448, 0x0449, 0x044a, 0x044b, 0x044c, 0x044d, 0x044e, 0x044f
];

const CP1251_REVERSE = new Map();
for (let i = 0; i < 128; i += 1) {
    CP1251_REVERSE.set(String.fromCharCode(i), i);
}
for (let i = 0; i < CP1251_TABLE.length; i += 1) {
    CP1251_REVERSE.set(String.fromCharCode(CP1251_TABLE[i]), 0x80 + i);
}

function decodeLatin1(value) {
    const bytes = Uint8Array.from(value, (char) => char.charCodeAt(0) & 0xff);
    return new TextDecoder('utf-8').decode(bytes);
}

function decodeCp1251(value) {
    const bytes = Uint8Array.from(value, (char) => CP1251_REVERSE.get(char) ?? 0x3f);
    return new TextDecoder('utf-8').decode(bytes);
}

function scoreReadable(value) {
    const russian = value.match(RUS_LETTER_RE)?.length || 0;
    const latin = value.match(LATIN_LETTER_RE)?.length || 0;
    const weird = value.match(WEIRD_CYRILLIC_RE)?.length || 0;
    return russian * 2 - latin - weird * 3;
}

function smartDecode(value, decoder) {
    const decoded = decoder(value);
    if (decoded === value) {
        return value;
    }
    if (scoreReadable(decoded) > scoreReadable(value)) {
        return decoded;
    }
    return value;
}

export function normalizeMojibakeText(value) {
    if (typeof value !== 'string') {
        return value;
    }
    let result = value;
    if (MOJIBAKE_LATIN_RE.test(result)) {
        try {
            result = smartDecode(result, decodeLatin1);
        } catch {
            // Keep original text when decoding fails.
        }
    }
    if (MOJIBAKE_CP1251_RE.test(result) || MOJIBAKE_RU_RE.test(result)) {
        try {
            result = smartDecode(result, decodeCp1251);
        } catch {
            // Keep original text when decoding fails.
        }
    }
    return result;
}
