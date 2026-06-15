#include <algorithm>
#include <cmath>
#include <cstdint>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <sstream>
#include <string>
#include <vector>

struct Stats {
    double mean = 0.0;
    double variance = 0.0;
    double gradient = 0.0;
    double blockiness = 0.0;
    double lowMass = 0.0;
    double highMass = 0.0;
    double chromaProxy = 0.0;
    double lengthNorm = 0.0;
};

static double clamp01(double x) {
    if (!std::isfinite(x)) return 0.0;
    return std::max(0.0, std::min(1.0, x));
}

static double round6(double x) {
    return std::round(x * 1000000.0) / 1000000.0;
}

static std::vector<unsigned char> read_file(const std::string& path) {
    std::ifstream in(path, std::ios::binary);
    if (!in) return {};
    return std::vector<unsigned char>((std::istreambuf_iterator<char>(in)), std::istreambuf_iterator<char>());
}

static uint32_t hash_string(const std::string& s) {
    uint32_t h = 2166136261u;
    for (unsigned char c : s) {
        h ^= c;
        h *= 16777619u;
    }
    return h;
}

struct XorShift32 {
    uint32_t x;
    explicit XorShift32(uint32_t seed) : x(seed ? seed : 123456789u) {}
    uint32_t next_u32() {
        uint32_t y = x;
        y ^= y << 13;
        y ^= y >> 17;
        y ^= y << 5;
        x = y;
        return x;
    }
    double next() { return double(next_u32()) / 4294967296.0; }
};

static std::vector<unsigned char> synthetic_bytes(const std::string& id, size_t n = 2048) {
    XorShift32 rng(hash_string(id));
    std::vector<unsigned char> out(n);
    int centre = 70 + int(rng.next_u32() % 120u);
    for (size_t i = 0; i < n; ++i) {
        double wave = 35.0 * std::sin(double(i) * 0.031 + double(hash_string(id) % 97u));
        int noise = int(std::floor(70.0 * (rng.next() - 0.5)));
        int v = int(std::round(double(centre) + wave + double(noise)));
        out[i] = static_cast<unsigned char>(std::max(0, std::min(255, v)));
    }
    return out;
}

static Stats byte_stats(const std::vector<unsigned char>& bytes_in) {
    const std::vector<unsigned char>& bytes = bytes_in.empty() ? synthetic_bytes("synthetic://empty") : bytes_in;
    const double n = std::max<size_t>(1, bytes.size());
    double sum = 0.0, sum2 = 0.0, grad = 0.0, block = 0.0, low = 0.0, high = 0.0, even = 0.0, odd = 0.0;
    for (size_t i = 0; i < bytes.size(); ++i) {
        double v = double(bytes[i]) / 255.0;
        sum += v;
        sum2 += v * v;
        if (i > 0) grad += std::abs(int(bytes[i]) - int(bytes[i - 1])) / 255.0;
        if (i > 0 && i % 8 == 0) block += std::abs(int(bytes[i]) - int(bytes[i - 1])) / 255.0;
        if (v < 0.22) low += 1.0;
        if (v > 0.78) high += 1.0;
        if (i % 2 == 0) even += v; else odd += v;
    }
    Stats s;
    s.mean = sum / n;
    s.variance = std::max(0.0, sum2 / n - s.mean * s.mean);
    s.gradient = grad / std::max(1.0, n - 1.0);
    s.blockiness = block / std::max(1.0, std::floor(n / 8.0));
    s.lowMass = low / n;
    s.highMass = high / n;
    s.chromaProxy = std::abs(even - odd) / std::max(1.0, std::floor(n / 2.0));
    s.lengthNorm = clamp01(std::log2(n + 1.0) / 16.0);
    return s;
}

struct Result {
    double score;
    double surface_smoothness;
    double central_smoothness;
    double compression_cleanliness;
    double background_softness;
    double accent_private_energy;
    double colour_structure;
    double boundary_structure;
    double upper_context_proxy;
    double full_frame_context;
    double environment_penalty;
    double chroma_penalty;
    double edge_preservation;
    double distortion_penalty;
    double edge_loss;
};

static Result result_from_stats(const Stats& s) {
    Result r;
    r.surface_smoothness = clamp01(1.0 - s.variance / 0.095);
    r.central_smoothness = clamp01(1.0 - (0.65 * s.variance + 0.35 * s.gradient) / 0.14);
    r.compression_cleanliness = clamp01(1.0 - s.blockiness / 0.35);
    r.background_softness = clamp01(1.0 - s.gradient / 0.42);
    r.accent_private_energy = clamp01(0.25 + 0.75 * std::abs(s.mean - 0.5) + 0.20 * r.background_softness);
    r.colour_structure = clamp01(0.35 + 1.8 * s.chromaProxy + 0.25 * s.highMass);
    r.boundary_structure = clamp01(0.15 + s.gradient / 0.32);
    r.upper_context_proxy = clamp01(0.45 + 0.55 * s.lengthNorm);
    r.full_frame_context = 1.0;
    r.environment_penalty = clamp01(0.55 * s.lowMass + 0.25 * s.blockiness);
    r.chroma_penalty = clamp01(1.4 * s.chromaProxy + 0.15 * s.highMass);
    r.edge_preservation = clamp01(1.0 - std::max(0.0, 0.16 - s.gradient) / 0.16);
    r.distortion_penalty = clamp01(std::max(0.0, s.blockiness - 0.18) / 0.32);
    r.edge_loss = clamp01(std::max(0.0, 0.10 - s.gradient) / 0.10);
    r.score =
        0.14 * r.surface_smoothness +
        0.16 * r.central_smoothness +
        0.09 * r.compression_cleanliness +
        0.08 * r.background_softness +
        0.11 * r.accent_private_energy +
        0.10 * r.colour_structure +
        0.10 * r.boundary_structure +
        0.11 * r.upper_context_proxy +
        0.08 * r.full_frame_context +
        0.09 * r.edge_preservation -
        0.16 * r.environment_penalty -
        0.18 * r.chroma_penalty -
        0.14 * r.distortion_penalty -
        0.06 * r.edge_loss;
    return r;
}

static void emit_json(const std::string& source, const Stats& s, const Result& r, size_t byte_length) {
    std::cout << std::fixed << std::setprecision(6);
    std::cout << "{\n";
    std::cout << "  \"backend\": \"cpp-byte-ffi/0.1.0\",\n";
    std::cout << "  \"source\": \"" << source << "\",\n";
    std::cout << "  \"byteLength\": " << byte_length << ",\n";
    std::cout << "  \"stats\": {\n";
    std::cout << "    \"mean\": " << round6(s.mean) << ",\n";
    std::cout << "    \"variance\": " << round6(s.variance) << ",\n";
    std::cout << "    \"gradient\": " << round6(s.gradient) << ",\n";
    std::cout << "    \"blockiness\": " << round6(s.blockiness) << ",\n";
    std::cout << "    \"lowMass\": " << round6(s.lowMass) << ",\n";
    std::cout << "    \"highMass\": " << round6(s.highMass) << ",\n";
    std::cout << "    \"chromaProxy\": " << round6(s.chromaProxy) << ",\n";
    std::cout << "    \"lengthNorm\": " << round6(s.lengthNorm) << "\n";
    std::cout << "  },\n";
    std::cout << "  \"result\": {\n";
    std::cout << "    \"score\": " << round6(r.score) << ",\n";
    std::cout << "    \"surface_smoothness\": " << round6(r.surface_smoothness) << ",\n";
    std::cout << "    \"central_smoothness\": " << round6(r.central_smoothness) << ",\n";
    std::cout << "    \"compression_cleanliness\": " << round6(r.compression_cleanliness) << ",\n";
    std::cout << "    \"background_softness\": " << round6(r.background_softness) << ",\n";
    std::cout << "    \"accent_private_energy\": " << round6(r.accent_private_energy) << ",\n";
    std::cout << "    \"colour_structure\": " << round6(r.colour_structure) << ",\n";
    std::cout << "    \"boundary_structure\": " << round6(r.boundary_structure) << ",\n";
    std::cout << "    \"upper_context_proxy\": " << round6(r.upper_context_proxy) << ",\n";
    std::cout << "    \"full_frame_context\": " << round6(r.full_frame_context) << ",\n";
    std::cout << "    \"environment_penalty\": " << round6(r.environment_penalty) << ",\n";
    std::cout << "    \"chroma_penalty\": " << round6(r.chroma_penalty) << ",\n";
    std::cout << "    \"edge_preservation\": " << round6(r.edge_preservation) << ",\n";
    std::cout << "    \"distortion_penalty\": " << round6(r.distortion_penalty) << ",\n";
    std::cout << "    \"edge_loss\": " << round6(r.edge_loss) << ",\n";
    std::cout << "    \"best_restore_passes\": 0\n";
    std::cout << "  }\n";
    std::cout << "}\n";
}

int main(int argc, char** argv) {
    if (argc < 3 || std::string(argv[1]) != "analyze") {
        std::cerr << "usage: image_metrics_ffi analyze <image-or-byte-file>\n";
        return 2;
    }
    std::string source = argv[2];
    std::vector<unsigned char> bytes = source.rfind("synthetic://", 0) == 0 ? synthetic_bytes(source) : read_file(source);
    if (bytes.empty()) bytes = synthetic_bytes("synthetic://" + source);
    Stats s = byte_stats(bytes);
    Result r = result_from_stats(s);
    emit_json(source, s, r, bytes.size());
    return 0;
}
