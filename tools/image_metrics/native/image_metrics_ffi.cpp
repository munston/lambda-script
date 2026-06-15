#include <algorithm>
#include <cmath>
#include <cstdint>
#include <cstdlib>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <iterator>
#include <sstream>
#include <string>
#include <vector>

#ifdef _WIN32
#ifndef NOMINMAX
#define NOMINMAX
#endif
#include <windows.h>
#include <wincodec.h>
#endif

struct Frame {
    int w = 0;
    int h = 0;
    std::vector<double> rgb;
};

struct Metric {
    double score = 0.0;
    double surface = 0.0;
    double central = 0.0;
    double compression = 0.0;
    double background = 0.0;
    double accent = 0.0;
    double colour = 0.0;
    double boundary = 0.0;
    double upper = 0.0;
    double full = 1.0;
    double env = 0.0;
    double chroma = 0.0;
    double edge = 0.0;
    double distort = 0.0;
    double edgeLoss = 0.0;
};

struct Atom {
    int index = 0;
    uint32_t seed = 0;
    double cx = 0.0;
    double cy = 0.0;
    double sigma = 0.0;
    int channel = 0;
    double scale = 0.0;
};

static double clamp01(double x) {
    if (!std::isfinite(x)) return 0.0;
    return std::max(0.0, std::min(1.0, x));
}

static double round6(double x) {
    return std::round(x * 1000000.0) / 1000000.0;
}

static uint32_t mix32(uint32_t x) {
    x ^= x >> 16;
    x *= 0x7feb352du;
    x ^= x >> 15;
    x *= 0x846ca68bu;
    x ^= x >> 16;
    return x;
}

static uint32_t hash_string(const std::string& s) {
    uint32_t h = 2166136261u;
    for (unsigned char c : s) {
        h ^= c;
        h *= 16777619u;
    }
    return h;
}

struct Rng {
    uint32_t x;
    explicit Rng(uint32_t seed) : x(seed ? seed : 123456789u) {}
    uint32_t u32() {
        uint32_t y = x;
        y ^= y << 13;
        y ^= y >> 17;
        y ^= y << 5;
        x = y;
        return x;
    }
    double next() { return double(u32()) / 4294967296.0; }
    double normal() {
        double u = std::max(1e-12, next());
        double v = std::max(1e-12, next());
        return std::sqrt(-2.0 * std::log(u)) * std::cos(2.0 * 3.14159265358979323846 * v);
    }
};

static double normal_from_seed(uint32_t seed) {
    Rng r(seed);
    return r.normal();
}

static std::string json_escape(const std::string& s) {
    std::ostringstream out;
    for (char c : s) {
        if (c == '\\') out << "\\\\";
        else if (c == '"') out << "\\\"";
        else if (c == '\n') out << "\\n";
        else out << c;
    }
    return out.str();
}

static std::vector<unsigned char> read_file_bytes(const std::string& path) {
    std::ifstream in(path, std::ios::binary);
    if (!in) return {};
    return std::vector<unsigned char>((std::istreambuf_iterator<char>(in)), std::istreambuf_iterator<char>());
}

static Frame synthetic_frame(const std::string& id, int w = 192, int h = 192) {
    Rng rng(hash_string(id));
    Frame f;
    f.w = w;
    f.h = h;
    f.rgb.assign(size_t(w * h * 3), 0.0);
    double phase = double(hash_string(id) % 1000u) / 1000.0;
    for (int y = 0; y < h; ++y) {
        for (int x = 0; x < w; ++x) {
            double nx = double(x) / std::max(1, w - 1);
            double ny = double(y) / std::max(1, h - 1);
            double base = 0.42 + 0.28 * nx + 0.15 * std::sin(6.28318530718 * (nx * 2.3 + ny * 1.7 + phase));
            double centre = std::exp(-((nx - 0.52) * (nx - 0.52) / 0.055 + (ny - 0.46) * (ny - 0.46) / 0.080));
            double dark = std::exp(-((nx - 0.76) * (nx - 0.76) / 0.020 + (ny - 0.55) * (ny - 0.55) / 0.060));
            size_t i = size_t((y * w + x) * 3);
            f.rgb[i + 0] = clamp01(base + 0.18 * centre - 0.20 * dark + 0.025 * rng.normal());
            f.rgb[i + 1] = clamp01(base + 0.12 * centre - 0.18 * dark + 0.025 * rng.normal());
            f.rgb[i + 2] = clamp01(base + 0.08 * centre - 0.14 * dark + 0.025 * rng.normal());
        }
    }
    return f;
}

#ifdef _WIN32
static std::wstring utf8_to_wide(const std::string& s) {
    int n = MultiByteToWideChar(CP_UTF8, 0, s.c_str(), -1, nullptr, 0);
    if (n <= 0) return L"";
    std::wstring out(size_t(n - 1), L'\0');
    MultiByteToWideChar(CP_UTF8, 0, s.c_str(), -1, &out[0], n);
    return out;
}

static Frame load_with_wic(const std::string& path) {
    Frame f;
    HRESULT hr = S_OK;
    bool coinit = false;
    IWICImagingFactory* factory = nullptr;
    IWICBitmapDecoder* decoder = nullptr;
    IWICBitmapFrameDecode* frame = nullptr;
    IWICFormatConverter* converter = nullptr;
    UINT w = 0;
    UINT h = 0;
    std::vector<unsigned char> bytes;
    std::wstring wide;

    hr = CoInitializeEx(nullptr, COINIT_MULTITHREADED);
    if (SUCCEEDED(hr)) coinit = true;
    if (hr == RPC_E_CHANGED_MODE) hr = S_OK;
    if (FAILED(hr)) goto done;

    hr = CoCreateInstance(CLSID_WICImagingFactory, nullptr, CLSCTX_INPROC_SERVER, IID_PPV_ARGS(&factory));
    if (FAILED(hr)) goto done;

    wide = utf8_to_wide(path);
    if (wide.empty()) goto done;

    hr = factory->CreateDecoderFromFilename(wide.c_str(), nullptr, GENERIC_READ, WICDecodeMetadataCacheOnLoad, &decoder);
    if (FAILED(hr)) goto done;

    hr = decoder->GetFrame(0, &frame);
    if (FAILED(hr)) goto done;

    hr = factory->CreateFormatConverter(&converter);
    if (FAILED(hr)) goto done;

    hr = converter->Initialize(frame, GUID_WICPixelFormat32bppRGBA, WICBitmapDitherTypeNone, nullptr, 0.0, WICBitmapPaletteTypeCustom);
    if (FAILED(hr)) goto done;

    hr = converter->GetSize(&w, &h);
    if (FAILED(hr) || w == 0 || h == 0) goto done;

    bytes.assign(size_t(w) * size_t(h) * 4u, 0);
    hr = converter->CopyPixels(nullptr, w * 4u, UINT(bytes.size()), bytes.data());
    if (FAILED(hr)) goto done;

    f.w = int(w);
    f.h = int(h);
    f.rgb.assign(size_t(w) * size_t(h) * 3u, 0.0);
    for (size_t i = 0, j = 0; i < bytes.size(); i += 4, j += 3) {
        f.rgb[j + 0] = double(bytes[i + 0]) / 255.0;
        f.rgb[j + 1] = double(bytes[i + 1]) / 255.0;
        f.rgb[j + 2] = double(bytes[i + 2]) / 255.0;
    }

done:
    if (converter) converter->Release();
    if (frame) frame->Release();
    if (decoder) decoder->Release();
    if (factory) factory->Release();
    if (coinit) CoUninitialize();
    return f;
}
#endif

static Frame load_frame(const std::string& source) {
    if (source.rfind("synthetic://", 0) == 0) return synthetic_frame(source);
#ifdef _WIN32
    {
        Frame decoded = load_with_wic(source);
        if (decoded.w > 0 && decoded.h > 0 && !decoded.rgb.empty()) return decoded;
    }
#endif
    return Frame();
}

static bool valid_frame(const Frame& f) {
    return f.w > 0 && f.h > 0 && !f.rgb.empty();
}

static void ensure_dir(const std::string& dir) {
#ifdef _WIN32
    CreateDirectoryA(dir.c_str(), nullptr);
#else
    std::string cmd = "mkdir -p '" + dir + "'";
    std::system(cmd.c_str());
#endif
}

static bool write_ppm(const std::string& path, const Frame& f) {
    std::ofstream out(path, std::ios::binary);
    if (!out) return false;
    out << "P6\n" << f.w << " " << f.h << "\n255\n";
    for (double v : f.rgb) {
        unsigned char b = (unsigned char)std::max(0, std::min(255, int(std::round(clamp01(v) * 255.0))));
        out.write((const char*)&b, 1);
    }
    return true;
}

static bool write_bmp(const std::string& path, const Frame& f) {
    std::ofstream out(path, std::ios::binary);
    if (!out) return false;
    int row = ((f.w * 3 + 3) / 4) * 4;
    int dataSize = row * f.h;
    int fileSize = 54 + dataSize;
    unsigned char header[54] = {};
    header[0] = 'B';
    header[1] = 'M';
    header[2] = fileSize & 255;
    header[3] = (fileSize >> 8) & 255;
    header[4] = (fileSize >> 16) & 255;
    header[5] = (fileSize >> 24) & 255;
    header[10] = 54;
    header[14] = 40;
    header[18] = f.w & 255;
    header[19] = (f.w >> 8) & 255;
    header[20] = (f.w >> 16) & 255;
    header[21] = (f.w >> 24) & 255;
    header[22] = f.h & 255;
    header[23] = (f.h >> 8) & 255;
    header[24] = (f.h >> 16) & 255;
    header[25] = (f.h >> 24) & 255;
    header[26] = 1;
    header[28] = 24;
    out.write((const char*)header, 54);
    std::vector<unsigned char> scan(size_t(row), 0);
    for (int y = f.h - 1; y >= 0; --y) {
        std::fill(scan.begin(), scan.end(), 0);
        for (int x = 0; x < f.w; ++x) {
            size_t src = size_t((y * f.w + x) * 3);
            size_t dst = size_t(x * 3);
            scan[dst + 0] = (unsigned char)std::max(0, std::min(255, int(std::round(clamp01(f.rgb[src + 2]) * 255.0))));
            scan[dst + 1] = (unsigned char)std::max(0, std::min(255, int(std::round(clamp01(f.rgb[src + 1]) * 255.0))));
            scan[dst + 2] = (unsigned char)std::max(0, std::min(255, int(std::round(clamp01(f.rgb[src + 0]) * 255.0))));
        }
        out.write((const char*)scan.data(), row);
    }
    return true;
}

static Metric score_frame(const Frame& f) {
    int w = f.w, h = f.h;
    double sum = 0.0, sum2 = 0.0, grad = 0.0, block = 0.0, low = 0.0, high = 0.0, chroma = 0.0;
    int n = std::max(1, w * h);
    for (int y = 0; y < h; ++y) {
        for (int x = 0; x < w; ++x) {
            size_t i = size_t((y * w + x) * 3);
            double r = f.rgb[i], g = f.rgb[i + 1], b = f.rgb[i + 2];
            double lum = 0.299 * r + 0.587 * g + 0.114 * b;
            sum += lum;
            sum2 += lum * lum;
            low += lum < 0.22 ? 1.0 : 0.0;
            high += lum > 0.78 ? 1.0 : 0.0;
            chroma += (std::abs(r - g) + std::abs(g - b) + std::abs(r - b)) / 3.0;
            if (x > 0) {
                size_t j = i - 3;
                double lum2 = 0.299 * f.rgb[j] + 0.587 * f.rgb[j + 1] + 0.114 * f.rgb[j + 2];
                grad += std::abs(lum - lum2);
                if (x % 8 == 0) block += std::abs(lum - lum2);
            }
            if (y > 0) {
                size_t j = size_t(((y - 1) * w + x) * 3);
                double lum2 = 0.299 * f.rgb[j] + 0.587 * f.rgb[j + 1] + 0.114 * f.rgb[j + 2];
                grad += std::abs(lum - lum2);
                if (y % 8 == 0) block += std::abs(lum - lum2);
            }
        }
    }
    double mean = sum / n;
    double variance = std::max(0.0, sum2 / n - mean * mean);
    double gradient = grad / std::max(1, 2 * n - w - h);
    double blockiness = block / std::max(1, (w / 8) * h + (h / 8) * w);
    double lowMass = low / n;
    double highMass = high / n;
    double chromaProxy = chroma / n;
    double lengthNorm = clamp01(std::log2(double(n) + 1.0) / 18.0);

    Metric m;
    m.surface = clamp01(1.0 - variance / 0.095);
    m.central = clamp01(1.0 - (0.65 * variance + 0.35 * gradient) / 0.14);
    m.compression = clamp01(1.0 - blockiness / 0.35);
    m.background = clamp01(1.0 - gradient / 0.42);
    m.accent = clamp01(0.25 + 0.75 * std::abs(mean - 0.5) + 0.20 * m.background);
    m.colour = clamp01(0.35 + 1.8 * chromaProxy + 0.25 * highMass);
    m.boundary = clamp01(0.15 + gradient / 0.32);
    m.upper = clamp01(0.45 + 0.55 * lengthNorm);
    m.full = 1.0;
    m.env = clamp01(0.55 * lowMass + 0.25 * blockiness);
    m.chroma = clamp01(1.4 * chromaProxy + 0.15 * highMass);
    m.edge = clamp01(1.0 - std::max(0.0, 0.16 - gradient) / 0.16);
    m.distort = clamp01(std::max(0.0, blockiness - 0.18) / 0.32);
    m.edgeLoss = clamp01(std::max(0.0, 0.10 - gradient) / 0.10);
    m.score = 0.14 * m.surface + 0.16 * m.central + 0.09 * m.compression + 0.08 * m.background + 0.11 * m.accent + 0.10 * m.colour + 0.10 * m.boundary + 0.11 * m.upper + 0.08 * m.full + 0.09 * m.edge - 0.16 * m.env - 0.18 * m.chroma - 0.14 * m.distort - 0.06 * m.edgeLoss;
    return m;
}

static std::string metric_json(const Metric& m) {
    std::ostringstream out;
    out << std::fixed << std::setprecision(6);
    out << "{";
    out << "\"score\":" << round6(m.score);
    out << ",\"surface_smoothness\":" << round6(m.surface);
    out << ",\"central_smoothness\":" << round6(m.central);
    out << ",\"compression_cleanliness\":" << round6(m.compression);
    out << ",\"background_softness\":" << round6(m.background);
    out << ",\"accent_private_energy\":" << round6(m.accent);
    out << ",\"colour_structure\":" << round6(m.colour);
    out << ",\"boundary_structure\":" << round6(m.boundary);
    out << ",\"upper_context_proxy\":" << round6(m.upper);
    out << ",\"full_frame_context\":" << round6(m.full);
    out << ",\"environment_penalty\":" << round6(m.env);
    out << ",\"chroma_penalty\":" << round6(m.chroma);
    out << ",\"edge_preservation\":" << round6(m.edge);
    out << ",\"distortion_penalty\":" << round6(m.distort);
    out << ",\"edge_loss\":" << round6(m.edgeLoss);
    out << ",\"best_restore_passes\":0";
    out << "}";
    return out.str();
}

static std::vector<Atom> make_support(uint32_t seed, int count, int w, int h, double step) {
    std::vector<Atom> atoms;
    atoms.reserve(std::max(0, count));
    Rng rng(seed ^ 0x9e3779b9u);
    for (int i = 0; i < count; ++i) {
        Atom a;
        a.index = i;
        a.seed = mix32(seed ^ uint32_t(0x85ebca6bu * (i + 1)));
        a.cx = rng.next() * std::max(1, w - 1);
        a.cy = rng.next() * std::max(1, h - 1);
        a.sigma = std::max(3.0, 0.035 * std::min(w, h) + rng.next() * 0.085 * std::min(w, h));
        a.channel = int(rng.u32() % 3u);
        a.scale = step * (0.65 + 0.70 * rng.next());
        atoms.push_back(a);
    }
    return atoms;
}

static void apply_atom(Frame& f, const Atom& a, double coeff) {
    double twoSigma2 = 2.0 * a.sigma * a.sigma;
    int radius = int(std::ceil(3.0 * a.sigma));
    int x0 = std::max(0, int(std::floor(a.cx)) - radius);
    int x1 = std::min(f.w - 1, int(std::floor(a.cx)) + radius);
    int y0 = std::max(0, int(std::floor(a.cy)) - radius);
    int y1 = std::min(f.h - 1, int(std::floor(a.cy)) + radius);
    for (int y = y0; y <= y1; ++y) {
        for (int x = x0; x <= x1; ++x) {
            double dx = double(x) - a.cx;
            double dy = double(y) - a.cy;
            double envelope = std::exp(-(dx * dx + dy * dy) / twoSigma2);
            for (int c = 0; c < 3; ++c) {
                uint32_t s = mix32(a.seed ^ uint32_t(x * 73856093u) ^ uint32_t(y * 19349663u) ^ uint32_t(c * 83492791u));
                double matrix = normal_from_seed(s);
                double channelWeight = (c == a.channel) ? 1.0 : 0.35;
                size_t idx = size_t((y * f.w + x) * 3 + c);
                f.rgb[idx] = clamp01(f.rgb[idx] + coeff * envelope * matrix * channelWeight);
            }
        }
    }
}

static int cmd_analyze(const std::string& source) {
    Frame f = load_frame(source);
    if (!valid_frame(f)) {
        std::cerr << "failed to decode image as real pixels: " << source << "\n";
        return 3;
    }
    Metric m = score_frame(f);
    std::cout << "{\n";
    std::cout << "  \"backend\": \"cpp-real-pixel-sparse-gaussian-ffi/0.3.2\",\n";
    std::cout << "  \"source\": \"" << json_escape(source) << "\",\n";
    std::cout << "  \"width\": " << f.w << ",\n";
    std::cout << "  \"height\": " << f.h << ",\n";
    std::cout << "  \"result\": " << metric_json(m) << "\n";
    std::cout << "}\n";
    return 0;
}

static int cmd_update(int argc, char** argv) {
    if (argc < 8) {
        std::cerr << "usage: image_metrics_ffi stochastic-update <image> <out-dir> <seed> <trials> <support> <step>\n";
        return 2;
    }
    std::string source = argv[2];
    std::string outDir = argv[3];
    uint32_t seed = uint32_t(std::strtoul(argv[4], nullptr, 10));
    int trials = std::max(1, std::atoi(argv[5]));
    int support = std::max(1, std::atoi(argv[6]));
    double step = std::max(0.0, std::atof(argv[7]));

    ensure_dir(outDir);
    Frame original = load_frame(source);
    if (!valid_frame(original)) {
        std::cerr << "failed to decode image as real pixels: " << source << "\n";
        return 3;
    }
    Frame best = original;
    Metric initial = score_frame(best);
    Metric bestMetric = initial;
    std::vector<Atom> atoms = make_support(seed, support, original.w, original.h, step);
    Rng rng(seed ^ 0x51f15eedu);
    int accepted = 0;

    std::ofstream trace(outDir + "/update_trace.json");
    trace << "[\n";
    for (int t = 0; t < trials; ++t) {
        Frame cand = best;
        int active = 0;
        std::vector<int> activeIdx;
        for (int j = 0; j < support; ++j) {
            if (rng.next() < 0.23) {
                active++;
                activeIdx.push_back(j);
                double coeff = atoms[j].scale * rng.normal();
                apply_atom(cand, atoms[j], coeff);
            }
        }
        Metric cm = score_frame(cand);
        bool ok = cm.score > bestMetric.score;
        if (ok) {
            best = cand;
            bestMetric = cm;
            accepted++;
            for (int j : activeIdx) atoms[j].scale = std::min(step * 5.0, atoms[j].scale * 1.025 + step * 0.002);
        } else {
            for (int j : activeIdx) atoms[j].scale = std::max(step * 0.04, atoms[j].scale * 0.996);
        }
        trace << (t ? ",\n" : "");
        trace << "  {\"trial\":" << t << ",\"score\":" << round6(cm.score) << ",\"best_score\":" << round6(bestMetric.score) << ",\"accepted\":" << (ok ? "true" : "false") << ",\"active\":" << active << "}";
    }
    trace << "\n]\n";

    write_ppm(outDir + "/source.ppm", original);
    write_ppm(outDir + "/updated.ppm", best);
    write_bmp(outDir + "/source.bmp", original);
    write_bmp(outDir + "/updated.bmp", best);

    std::ofstream dict(outDir + "/support_dictionary.json");
    dict << "[\n";
    for (size_t i = 0; i < atoms.size(); ++i) {
        const Atom& a = atoms[i];
        dict << (i ? ",\n" : "");
        dict << "  {\"index\":" << a.index << ",\"seed\":" << a.seed << ",\"cx\":" << round6(a.cx) << ",\"cy\":" << round6(a.cy) << ",\"sigma\":" << round6(a.sigma) << ",\"channel\":" << a.channel << ",\"scale\":" << round6(a.scale) << "}";
    }
    dict << "\n]\n";

    std::ofstream report(outDir + "/report.json");
    report << "{\n";
    report << "  \"backend\": \"cpp-real-pixel-sparse-gaussian-ffi/0.3.2\",\n";
    report << "  \"source\": \"" << json_escape(source) << "\",\n";
    report << "  \"width\": " << original.w << ",\n";
    report << "  \"height\": " << original.h << ",\n";
    report << "  \"seed\": " << seed << ",\n";
    report << "  \"trials\": " << trials << ",\n";
    report << "  \"support\": " << support << ",\n";
    report << "  \"step\": " << round6(step) << ",\n";
    report << "  \"accepted\": " << accepted << ",\n";
    report << "  \"initial_score\": " << round6(initial.score) << ",\n";
    report << "  \"final_score\": " << round6(bestMetric.score) << ",\n";
    report << "  \"increase\": " << round6(bestMetric.score - initial.score) << ",\n";
    report << "  \"initial\": " << metric_json(initial) << ",\n";
    report << "  \"final\": " << metric_json(bestMetric) << "\n";
    report << "}\n";

    std::ofstream summary(outDir + "/update_summary.txt");
    summary << "backend: cpp-real-pixel-sparse-gaussian-ffi/0.3.2\n";
    summary << "source: " << source << "\n";
    summary << "width: " << original.w << "\n";
    summary << "height: " << original.h << "\n";
    summary << "initial_score: " << std::fixed << std::setprecision(6) << initial.score << "\n";
    summary << "final_score: " << bestMetric.score << "\n";
    summary << "increase: " << bestMetric.score - initial.score << "\n";
    summary << "accepted: " << accepted << "/" << trials << "\n";
    summary << "outputs: source.bmp updated.bmp source.ppm updated.ppm report.json update_trace.json support_dictionary.json\n";

    std::cout << "{\n";
    std::cout << "  \"backend\": \"cpp-real-pixel-sparse-gaussian-ffi/0.3.2\",\n";
    std::cout << "  \"outDir\": \"" << json_escape(outDir) << "\",\n";
    std::cout << "  \"initial_score\": " << round6(initial.score) << ",\n";
    std::cout << "  \"final_score\": " << round6(bestMetric.score) << ",\n";
    std::cout << "  \"increase\": " << round6(bestMetric.score - initial.score) << ",\n";
    std::cout << "  \"accepted\": " << accepted << "\n";
    std::cout << "}\n";
    return 0;
}

int main(int argc, char** argv) {
    if (argc < 2) {
        std::cerr << "usage: image_metrics_ffi analyze <image> | stochastic-update <image> <out-dir> <seed> <trials> <support> <step>\n";
        return 2;
    }
    std::string cmd = argv[1];
    if (cmd == "analyze") {
        if (argc < 3) {
            std::cerr << "usage: image_metrics_ffi analyze <image>\n";
            return 2;
        }
        return cmd_analyze(argv[2]);
    }
    if (cmd == "stochastic-update") return cmd_update(argc, argv);
    std::cerr << "unknown command: " << cmd << "\n";
    return 2;
}
