#include <algorithm>
#include <cmath>
#include <cstdint>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <string>
#include <vector>

static double clamp01(double x){ return std::isfinite(x) ? std::max(0.0, std::min(1.0, x)) : 0.0; }
static double round6(double x){ return std::round(x * 1000000.0) / 1000000.0; }

static uint32_t hash_string(const std::string& s){
    uint32_t h = 2166136261u;
    for(unsigned char c: s){ h ^= c; h *= 16777619u; }
    return h;
}

struct Rng{
    uint32_t x;
    explicit Rng(uint32_t seed): x(seed ? seed : 123456789u){}
    uint32_t u32(){ uint32_t y=x; y^=y<<13; y^=y>>17; y^=y<<5; x=y; return x; }
    double next(){ return double(u32()) / 4294967296.0; }
};

static std::vector<unsigned char> synthetic_bytes(const std::string& id, size_t n=2048){
    Rng rng(hash_string(id));
    std::vector<unsigned char> out(n);
    int centre = 70 + int(rng.u32() % 120u);
    for(size_t i=0;i<n;i++){
        double wave = 35.0 * std::sin(double(i) * 0.031 + double(hash_string(id) % 97u));
        int noise = int(std::floor(70.0 * (rng.next() - 0.5)));
        out[i] = (unsigned char)std::max(0, std::min(255, int(std::round(double(centre)+wave+double(noise)))));
    }
    return out;
}

static std::vector<unsigned char> read_file(const std::string& path){
    std::ifstream in(path, std::ios::binary);
    if(!in) return {};
    return std::vector<unsigned char>((std::istreambuf_iterator<char>(in)), std::istreambuf_iterator<char>());
}

struct Stats{ double mean, variance, gradient, blockiness, lowMass, highMass, chromaProxy, lengthNorm; };

static Stats stats_from_bytes(const std::vector<unsigned char>& in){
    const std::vector<unsigned char> bytes = in.empty() ? synthetic_bytes("synthetic://empty") : in;
    double n = std::max<size_t>(1, bytes.size());
    double sum=0, sum2=0, grad=0, block=0, low=0, high=0, even=0, odd=0;
    for(size_t i=0;i<bytes.size();i++){
        double v = double(bytes[i]) / 255.0;
        sum += v; sum2 += v*v;
        if(i>0) grad += std::abs(int(bytes[i])-int(bytes[i-1])) / 255.0;
        if(i>0 && i%8==0) block += std::abs(int(bytes[i])-int(bytes[i-1])) / 255.0;
        if(v < 0.22) low += 1; if(v > 0.78) high += 1;
        if(i%2==0) even += v; else odd += v;
    }
    double mean = sum / n;
    return {
        mean,
        std::max(0.0, sum2/n - mean*mean),
        grad / std::max(1.0, n-1.0),
        block / std::max(1.0, std::floor(n/8.0)),
        low/n,
        high/n,
        std::abs(even-odd) / std::max(1.0, std::floor(n/2.0)),
        clamp01(std::log2(n+1.0)/16.0)
    };
}

int main(int argc, char** argv){
    if(argc < 3 || std::string(argv[1]) != "analyze"){
        std::cerr << "usage: image_metrics_ffi analyze <image-or-byte-file>\n";
        return 2;
    }
    std::string source = argv[2];
    std::vector<unsigned char> bytes = source.rfind("synthetic://",0)==0 ? synthetic_bytes(source) : read_file(source);
    if(bytes.empty()) bytes = synthetic_bytes("synthetic://" + source);
    Stats s = stats_from_bytes(bytes);
    double surface = clamp01(1.0 - s.variance / 0.095);
    double central = clamp01(1.0 - (0.65*s.variance + 0.35*s.gradient) / 0.14);
    double compression = clamp01(1.0 - s.blockiness / 0.35);
    double background = clamp01(1.0 - s.gradient / 0.42);
    double accent = clamp01(0.25 + 0.75*std::abs(s.mean-0.5) + 0.20*background);
    double colour = clamp01(0.35 + 1.8*s.chromaProxy + 0.25*s.highMass);
    double boundary = clamp01(0.15 + s.gradient / 0.32);
    double upper = clamp01(0.45 + 0.55*s.lengthNorm);
    double env = clamp01(0.55*s.lowMass + 0.25*s.blockiness);
    double chroma = clamp01(1.4*s.chromaProxy + 0.15*s.highMass);
    double edgePres = clamp01(1.0 - std::max(0.0, 0.16-s.gradient)/0.16);
    double distort = clamp01(std::max(0.0, s.blockiness-0.18)/0.32);
    double edgeLoss = clamp01(std::max(0.0, 0.10-s.gradient)/0.10);
    double score = 0.14*surface + 0.16*central + 0.09*compression + 0.08*background + 0.11*accent + 0.10*colour + 0.10*boundary + 0.11*upper + 0.08 + 0.09*edgePres - 0.16*env - 0.18*chroma - 0.14*distort - 0.06*edgeLoss;
    std::cout << std::fixed << std::setprecision(6);
    std::cout << "{\n";
    std::cout << "  \"backend\": \"cpp-byte-ffi/0.1.1\",\n";
    std::cout << "  \"source\": \"" << source << "\",\n";
    std::cout << "  \"byteLength\": " << bytes.size() << ",\n";
    std::cout << "  \"result\": {\n";
    std::cout << "    \"score\": " << round6(score) << ",\n";
    std::cout << "    \"surface_smoothness\": " << round6(surface) << ",\n";
    std::cout << "    \"central_smoothness\": " << round6(central) << ",\n";
    std::cout << "    \"compression_cleanliness\": " << round6(compression) << ",\n";
    std::cout << "    \"background_softness\": " << round6(background) << ",\n";
    std::cout << "    \"accent_private_energy\": " << round6(accent) << ",\n";
    std::cout << "    \"colour_structure\": " << round6(colour) << ",\n";
    std::cout << "    \"boundary_structure\": " << round6(boundary) << ",\n";
    std::cout << "    \"upper_context_proxy\": " << round6(upper) << ",\n";
    std::cout << "    \"full_frame_context\": 1.000000,\n";
    std::cout << "    \"environment_penalty\": " << round6(env) << ",\n";
    std::cout << "    \"chroma_penalty\": " << round6(chroma) << ",\n";
    std::cout << "    \"edge_preservation\": " << round6(edgePres) << ",\n";
    std::cout << "    \"distortion_penalty\": " << round6(distort) << ",\n";
    std::cout << "    \"edge_loss\": " << round6(edgeLoss) << ",\n";
    std::cout << "    \"best_restore_passes\": 0\n";
    std::cout << "  }\n";
    std::cout << "}\n";
    return 0;
}
