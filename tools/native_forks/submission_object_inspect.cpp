#include <array>
#include <cstdint>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>

namespace fs = std::filesystem;

static std::string read_file(const fs::path& path) {
    std::ifstream in(path, std::ios::binary);
    if (!in) throw std::runtime_error("cannot open file: " + path.string());
    std::ostringstream ss;
    ss << in.rdbuf();
    return ss.str();
}

static uint32_t rotr(uint32_t x, uint32_t n) { return (x >> n) | (x << (32 - n)); }
static std::string sha256_hex(const std::string& input) {
    static const uint32_t k[64] = {
        0x428a2f98,0x71374491,0xb5c0fbcf,0xe9b5dba5,0x3956c25b,0x59f111f1,0x923f82a4,0xab1c5ed5,
        0xd807aa98,0x12835b01,0x243185be,0x550c7dc3,0x72be5d74,0x80deb1fe,0x9bdc06a7,0xc19bf174,
        0xe49b69c1,0xefbe4786,0x0fc19dc6,0x240ca1cc,0x2de92c6f,0x4a7484aa,0x5cb0a9dc,0x76f988da,
        0x983e5152,0xa831c66d,0xb00327c8,0xbf597fc7,0xc6e00bf3,0xd5a79147,0x06ca6351,0x14292967,
        0x27b70a85,0x2e1b2138,0x4d2c6dfc,0x53380d13,0x650a7354,0x766a0abb,0x81c2c92e,0x92722c85,
        0xa2bfe8a1,0xa81a664b,0xc24b8b70,0xc76c51a3,0xd192e819,0xd6990624,0xf40e3585,0x106aa070,
        0x19a4c116,0x1e376c08,0x2748774c,0x34b0bcb5,0x391c0cb3,0x4ed8aa4a,0x5b9cca4f,0x682e6ff3,
        0x748f82ee,0x78a5636f,0x84c87814,0x8cc70208,0x90befffa,0xa4506ceb,0xbef9a3f7,0xc67178f2
    };
    uint64_t bit_len = static_cast<uint64_t>(input.size()) * 8ULL;
    std::vector<uint8_t> data(input.begin(), input.end());
    data.push_back(0x80);
    while ((data.size() % 64) != 56) data.push_back(0);
    for (int i = 7; i >= 0; --i) data.push_back(static_cast<uint8_t>((bit_len >> (i * 8)) & 0xff));
    uint32_t h[8] = {0x6a09e667,0xbb67ae85,0x3c6ef372,0xa54ff53a,0x510e527f,0x9b05688c,0x1f83d9ab,0x5be0cd19};
    for (size_t chunk = 0; chunk < data.size(); chunk += 64) {
        uint32_t w[64] = {};
        for (int i = 0; i < 16; ++i) {
            size_t j = chunk + i * 4;
            w[i] = (static_cast<uint32_t>(data[j]) << 24) | (static_cast<uint32_t>(data[j+1]) << 16) | (static_cast<uint32_t>(data[j+2]) << 8) | static_cast<uint32_t>(data[j+3]);
        }
        for (int i = 16; i < 64; ++i) {
            uint32_t s0 = rotr(w[i-15], 7) ^ rotr(w[i-15], 18) ^ (w[i-15] >> 3);
            uint32_t s1 = rotr(w[i-2], 17) ^ rotr(w[i-2], 19) ^ (w[i-2] >> 10);
            w[i] = w[i-16] + s0 + w[i-7] + s1;
        }
        uint32_t a=h[0], b=h[1], c=h[2], d=h[3], e=h[4], f=h[5], g=h[6], hh=h[7];
        for (int i = 0; i < 64; ++i) {
            uint32_t S1 = rotr(e, 6) ^ rotr(e, 11) ^ rotr(e, 25);
            uint32_t ch = (e & f) ^ ((~e) & g);
            uint32_t temp1 = hh + S1 + ch + k[i] + w[i];
            uint32_t S0 = rotr(a, 2) ^ rotr(a, 13) ^ rotr(a, 22);
            uint32_t maj = (a & b) ^ (a & c) ^ (b & c);
            uint32_t temp2 = S0 + maj;
            hh = g; g = f; f = e; e = d + temp1; d = c; c = b; b = a; a = temp1 + temp2;
        }
        h[0]+=a; h[1]+=b; h[2]+=c; h[3]+=d; h[4]+=e; h[5]+=f; h[6]+=g; h[7]+=hh;
    }
    std::ostringstream out;
    out << std::hex << std::setfill('0');
    for (uint32_t v : h) out << std::setw(8) << v;
    return out.str();
}

static size_t skip_ws(const std::string& s, size_t i) {
    while (i < s.size() && (s[i] == ' ' || s[i] == '\n' || s[i] == '\r' || s[i] == '\t')) ++i;
    return i;
}

static std::string parse_json_string_at(const std::string& s, size_t& i) {
    if (i >= s.size() || s[i] != '"') throw std::runtime_error("expected JSON string");
    ++i;
    std::string out;
    while (i < s.size()) {
        char c = s[i++];
        if (c == '"') return out;
        if (c == '\\') {
            if (i >= s.size()) throw std::runtime_error("unterminated JSON escape");
            char e = s[i++];
            switch (e) {
                case '"': out.push_back('"'); break;
                case '\\': out.push_back('\\'); break;
                case '/': out.push_back('/'); break;
                case 'b': out.push_back('\b'); break;
                case 'f': out.push_back('\f'); break;
                case 'n': out.push_back('\n'); break;
                case 'r': out.push_back('\r'); break;
                case 't': out.push_back('\t'); break;
                case 'u':
                    if (i + 4 > s.size()) throw std::runtime_error("short JSON unicode escape");
                    out.push_back('?');
                    i += 4;
                    break;
                default: throw std::runtime_error("unsupported JSON escape");
            }
        } else {
            out.push_back(c);
        }
    }
    throw std::runtime_error("unterminated JSON string");
}

static std::string require_string_field(const std::string& json, const std::string& key) {
    std::string needle = "\"" + key + "\"";
    size_t k = json.find(needle);
    if (k == std::string::npos) throw std::runtime_error("missing string field: " + key);
    size_t colon = json.find(':', k + needle.size());
    if (colon == std::string::npos) throw std::runtime_error("missing colon after field: " + key);
    size_t value = skip_ws(json, colon + 1);
    return parse_json_string_at(json, value);
}

static std::vector<std::string> optional_string_array_field(const std::string& json, const std::string& key) {
    std::vector<std::string> out;
    std::string needle = "\"" + key + "\"";
    size_t k = json.find(needle);
    if (k == std::string::npos) return out;
    size_t colon = json.find(':', k + needle.size());
    if (colon == std::string::npos) return out;
    size_t i = skip_ws(json, colon + 1);
    if (i >= json.size() || json[i] != '[') return out;
    ++i;
    while (i < json.size()) {
        i = skip_ws(json, i);
        if (i < json.size() && json[i] == ']') return out;
        out.push_back(parse_json_string_at(json, i));
        i = skip_ws(json, i);
        if (i < json.size() && json[i] == ',') { ++i; continue; }
        if (i < json.size() && json[i] == ']') return out;
        throw std::runtime_error("invalid string array field: " + key);
    }
    throw std::runtime_error("unterminated array field: " + key);
}

static std::string json_escape(const std::string& s) {
    std::ostringstream out;
    for (char c : s) {
        switch (c) {
            case '"': out << "\\\""; break;
            case '\\': out << "\\\\"; break;
            case '\b': out << "\\b"; break;
            case '\f': out << "\\f"; break;
            case '\n': out << "\\n"; break;
            case '\r': out << "\\r"; break;
            case '\t': out << "\\t"; break;
            default: out << c; break;
        }
    }
    return out.str();
}

int main(int argc, char** argv) {
    try {
        fs::path path;
        bool quiet = false;
        for (int i = 1; i < argc; ++i) {
            std::string arg = argv[i];
            if (arg == "--file" && i + 1 < argc) path = argv[++i];
            else if (arg == "--agent" && i + 1 < argc) path = fs::path(".forks") / "submissions" / (std::string(argv[++i]) + ".json");
            else if (arg == "--quiet") quiet = true;
            else if (arg == "--help") {
                std::cout << "usage: submission_object_inspect --file <path> [--quiet]\n"
                          << "   or: submission_object_inspect --agent <name> [--quiet]\n";
                return 0;
            } else {
                throw std::runtime_error("unknown or incomplete argument: " + arg);
            }
        }
        if (path.empty()) throw std::runtime_error("missing --file or --agent");
        std::string json = read_file(path);
        std::string format = require_string_field(json, "format");
        if (format != "LS_FORK_SUBMISSION_V1") throw std::runtime_error("invalid submission format: " + format);
        std::string agent = require_string_field(json, "agent");
        std::string source_ref = require_string_field(json, "source_ref");
        std::string patch = require_string_field(json, "patch");
        std::string expected_hash = require_string_field(json, "patch_sha256");
        std::string actual_hash = sha256_hex(patch);
        if (expected_hash != actual_hash) throw std::runtime_error("submission patch hash mismatch");
        std::vector<std::string> changed_files = optional_string_array_field(json, "changed_files");
        if (!quiet) {
            std::cout << "{\n"
                      << "  \"valid\": true,\n"
                      << "  \"format\": \"" << json_escape(format) << "\",\n"
                      << "  \"agent\": \"" << json_escape(agent) << "\",\n"
                      << "  \"source_ref\": \"" << json_escape(source_ref) << "\",\n"
                      << "  \"changed_files\": " << changed_files.size() << ",\n"
                      << "  \"patch_sha256\": \"" << json_escape(actual_hash) << "\"\n"
                      << "}\n";
        }
        return 0;
    } catch (const std::exception& e) {
        std::cerr << "submission_object_inspect: " << e.what() << "\n";
        return 1;
    }
}
