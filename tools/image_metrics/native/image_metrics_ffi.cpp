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
    int harmonicOrder = 0;
    double radialFrequency = 0.0;
    double phase = 0.0;
    double orientation = 0.0;
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


struct DeltaStats {
    double meanAbs = 0.0;
    double maxAbs = 0.0;
    double rms = 0.0;
};

static DeltaStats delta_stats(const Frame& a, const Frame& b) {
    DeltaStats d;
    if (a.w != b.w || a.h != b.h || a.rgb.size() != b.rgb.size() || a.rgb.empty()) return d;
    double sum = 0.0;
    double sum2 = 0.0;
    for (size_t i = 0; i < a.rgb.size(); ++i) {
        double v = std::abs(b.rgb[i] - a.rgb[i]);
        sum += v;
        sum2 += v * v;
        d.maxAbs = std::max(d.maxAbs, v);
    }
    d.meanAbs = sum / double(a.rgb.size());
    d.rms = std::sqrt(sum2 / double(a.rgb.size()));
    return d;
}

static Frame delta_frame(const Frame& a, const Frame& b, double gain) {
    Frame d;
    d.w = a.w;
    d.h = a.h;
    d.rgb.assign(a.rgb.size(), 0.0);
    if (a.w != b.w || a.h != b.h || a.rgb.size() != b.rgb.size()) return d;
    for (size_t i = 0; i < a.rgb.size(); ++i) {
        double diff = b.rgb[i] - a.rgb[i];
        d.rgb[i] = clamp01(0.5 + diff * gain);
    }
    return d;
}

static Frame visible_delta_overlay(const Frame& a, const Frame& b, double gain) {
    Frame o = a;
    if (a.w != b.w || a.h != b.h || a.rgb.size() != b.rgb.size()) return o;
    for (size_t i = 0; i < a.rgb.size(); i += 3) {
        double dr = b.rgb[i + 0] - a.rgb[i + 0];
        double dg = b.rgb[i + 1] - a.rgb[i + 1];
        double db = b.rgb[i + 2] - a.rgb[i + 2];
        double mag = std::sqrt((dr * dr + dg * dg + db * db) / 3.0);
        o.rgb[i + 0] = clamp01(a.rgb[i + 0] + gain * mag);
        o.rgb[i + 1] = clamp01(a.rgb[i + 1] - 0.35 * gain * mag);
        o.rgb[i + 2] = clamp01(a.rgb[i + 2] - 0.35 * gain * mag);
    }
    return o;
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
        a.harmonicOrder = int(rng.u32() % 5u);
        a.radialFrequency = 2.2 + 7.8 * rng.next();
        a.phase = 6.28318530717958647692 * rng.next();
        a.orientation = 6.28318530717958647692 * rng.next();
        atoms.push_back(a);
    }
    return atoms;
}

static double wrap_angle(double x) {
    const double tau = 6.28318530717958647692;
    while (x < 0.0) x += tau;
    while (x >= tau) x -= tau;
    return x;
}

static Atom perturb_atom(const Atom& base, Rng& rng, int w, int h, double step) {
    Atom a = base;
    double minDim = double(std::max(1, std::min(w, h)));
    double posStep = std::max(0.30, 0.55 * a.sigma);
    a.cx = std::max(0.0, std::min(double(std::max(1, w - 1)), a.cx + posStep * rng.normal()));
    a.cy = std::max(0.0, std::min(double(std::max(1, h - 1)), a.cy + posStep * rng.normal()));
    a.sigma = std::max(2.0, std::min(0.35 * minDim, a.sigma * std::exp(0.12 * rng.normal())));
    a.radialFrequency = std::max(0.45, std::min(18.0, a.radialFrequency * std::exp(0.10 * rng.normal())));
    a.phase = wrap_angle(a.phase + 0.35 * rng.normal());
    a.orientation = wrap_angle(a.orientation + 0.28 * rng.normal());
    if (rng.next() < 0.10) {
        int delta = rng.next() < 0.5 ? -1 : 1;
        a.harmonicOrder = std::max(0, std::min(8, a.harmonicOrder + delta));
    }
    if (rng.next() < 0.06) a.channel = int(rng.u32() % 3u);
    a.scale = std::max(step * 0.04, std::min(step * 3.0, a.scale * std::exp(0.08 * rng.normal())));
    return a;
}


static double bessel_j_int(int order, double x) {
    int m = std::max(0, std::min(8, order));
    double ax = std::abs(x);
    if (ax < 1e-9) return m == 0 ? 1.0 : 0.0;
#if defined(__cpp_lib_math_special_functions) && __cpp_lib_math_special_functions >= 201603L
    return std::cyl_bessel_j(m, ax);
#else
    double half = 0.5 * ax;
    double term = 1.0;
    for (int i = 1; i <= m; ++i) term *= half / double(i);
    double sum = term;
    for (int q = 0; q < 48; ++q) {
        term *= -(half * half) / (double(q + 1) * double(q + m + 1));
        sum += term;
        if (std::abs(term) < 1e-12) break;
    }
    return sum;
#endif
}

static double bessel_window_value(const Atom& a, int x, int y, int c) {
    double dx = double(x) - a.cx;
    double dy = double(y) - a.cy;
    double radius = std::sqrt(dx * dx + dy * dy);
    double sigma = std::max(1e-6, a.sigma);
    double rho = radius / sigma;
    double theta = std::atan2(dy, dx) - a.orientation;
    double window = std::exp(-0.5 * rho * rho);
    double radial = bessel_j_int(a.harmonicOrder, a.radialFrequency * rho);
    double angular = std::cos(double(a.harmonicOrder) * theta + a.phase);
    double channelPhase = (double(c) - double(a.channel)) * 2.09439510239319549;
    double channelMix = 0.72 + 0.28 * std::cos(channelPhase);
    return std::max(-1.0, std::min(1.0, window * radial * angular * channelMix));
}

static void apply_atom(Frame& f, const Atom& a, double coeff) {
    int radius = int(std::ceil(3.0 * a.sigma));
    int x0 = std::max(0, int(std::floor(a.cx)) - radius);
    int x1 = std::min(f.w - 1, int(std::floor(a.cx)) + radius);
    int y0 = std::max(0, int(std::floor(a.cy)) - radius);
    int y1 = std::min(f.h - 1, int(std::floor(a.cy)) + radius);
    for (int y = y0; y <= y1; ++y) {
        for (int x = x0; x <= x1; ++x) {
            for (int c = 0; c < 3; ++c) {
                double basis = bessel_window_value(a, x, y, c);
                double channelWeight = (c == a.channel) ? 1.0 : 0.40;
                size_t idx = size_t((y * f.w + x) * 3 + c);
                f.rgb[idx] = clamp01(f.rgb[idx] + coeff * basis * channelWeight);
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
    std::cout << "  \"backend\": \"cpp-localized-bessel-support-ffi/0.5.0\",\n";
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
    double bestObjective = initial.score;
    std::vector<Atom> atoms = make_support(seed, support, original.w, original.h, step);
    Rng rng(seed ^ 0x51f15eedu);
    int accepted = 0;

    std::ofstream trace(outDir + "/update_trace.json");
    trace << "[\n";
    for (int t = 0; t < trials; ++t) {
        Frame cand = best;
        int active = 0;
        std::vector<int> activeIdx;
        std::vector<Atom> proposed = atoms;
        for (int j = 0; j < support; ++j) {
            if (rng.next() < 0.23) {
                active++;
                activeIdx.push_back(j);
                proposed[j] = perturb_atom(atoms[j], rng, original.w, original.h, step);
                double coeff = proposed[j].scale * rng.normal();
                apply_atom(cand, proposed[j], coeff);
            }
        }
        Metric cm = score_frame(cand);
        DeltaStats candDelta = delta_stats(original, cand);
        double objective = cm.score - 0.70 * candDelta.rms - 0.18 * candDelta.maxAbs;
        bool ok = objective > bestObjective;
        if (ok) {
            best = cand;
            bestMetric = cm;
            bestObjective = objective;
            accepted++;
            for (int j : activeIdx) {
                atoms[j] = proposed[j];
                atoms[j].scale = std::min(step * 3.0, atoms[j].scale * 1.018 + step * 0.001);
            }
        } else {
            for (int j : activeIdx) atoms[j].scale = std::max(step * 0.04, atoms[j].scale * 0.992);
        }
        trace << (t ? ",\n" : "");
        trace << "  {\"trial\":" << t << ",\"score\":" << round6(cm.score) << ",\"objective\":" << round6(objective) << ",\"best_score\":" << round6(bestMetric.score) << ",\"best_objective\":" << round6(bestObjective) << ",\"accepted\":" << (ok ? "true" : "false") << ",\"active\":" << active << ",\"mean_abs_pixel_delta\":" << round6(candDelta.meanAbs) << ",\"max_abs_pixel_delta\":" << round6(candDelta.maxAbs) << ",\"rms_pixel_delta\":" << round6(candDelta.rms) << "}";
    }
    trace << "\n]\n";

    DeltaStats ds = delta_stats(original, best);
    Frame delta = delta_frame(original, best, 24.0);
    Frame deltaOverlay = visible_delta_overlay(original, best, 18.0);

    write_ppm(outDir + "/source.ppm", original);
    write_ppm(outDir + "/updated.ppm", best);
    write_ppm(outDir + "/delta.ppm", delta);
    write_ppm(outDir + "/delta_overlay.ppm", deltaOverlay);
    write_bmp(outDir + "/source.bmp", original);
    write_bmp(outDir + "/updated.bmp", best);
    write_bmp(outDir + "/delta.bmp", delta);
    write_bmp(outDir + "/delta_overlay.bmp", deltaOverlay);

    std::ofstream dict(outDir + "/support_dictionary.json");
    dict << "[\n";
    for (size_t i = 0; i < atoms.size(); ++i) {
        const Atom& a = atoms[i];
        dict << (i ? ",\n" : "");
        dict << "  {\"index\":" << a.index << ",\"seed\":" << a.seed << ",\"cx\":" << round6(a.cx) << ",\"cy\":" << round6(a.cy) << ",\"sigma\":" << round6(a.sigma) << ",\"channel\":" << a.channel << ",\"scale\":" << round6(a.scale) << ",\"harmonic_order\":" << a.harmonicOrder << ",\"radial_frequency\":" << round6(a.radialFrequency) << ",\"phase\":" << round6(a.phase) << ",\"orientation\":" << round6(a.orientation) << "}";
    }
    dict << "\n]\n";

    std::ofstream report(outDir + "/report.json");
    report << "{\n";
    report << "  \"backend\": \"cpp-localized-bessel-support-ffi/0.5.0\",\n";
    report << "  \"source\": \"" << json_escape(source) << "\",\n";
    report << "  \"width\": " << original.w << ",\n";
    report << "  \"height\": " << original.h << ",\n";
    report << "  \"seed\": " << seed << ",\n";
    report << "  \"trials\": " << trials << ",\n";
    report << "  \"support\": " << support << ",\n";
    report << "  \"support_mode\": \"localized_bessel_parameter_vector\",\n";
    report << "  \"step\": " << round6(step) << ",\n";
    report << "  \"accepted\": " << accepted << ",\n";
    report << "  \"mean_abs_pixel_delta\": " << round6(ds.meanAbs) << ",\n";
    report << "  \"max_abs_pixel_delta\": " << round6(ds.maxAbs) << ",\n";
    report << "  \"rms_pixel_delta\": " << round6(ds.rms) << ",\n";
    report << "  \"initial_score\": " << round6(initial.score) << ",\n";
    report << "  \"final_score\": " << round6(bestMetric.score) << ",\n";
    report << "  \"final_objective\": " << round6(bestObjective) << ",\n";
    report << "  \"increase\": " << round6(bestMetric.score - initial.score) << ",\n";
    report << "  \"initial\": " << metric_json(initial) << ",\n";
    report << "  \"final\": " << metric_json(bestMetric) << "\n";
    report << "}\n";

    std::ofstream summary(outDir + "/update_summary.txt");
    summary << "backend: cpp-localized-bessel-support-ffi/0.5.0\n";
    summary << "source: " << source << "\n";
    summary << "width: " << original.w << "\n";
    summary << "height: " << original.h << "\n";
    summary << "initial_score: " << std::fixed << std::setprecision(6) << initial.score << "\n";
    summary << "final_score: " << bestMetric.score << "\n";
    summary << "final_objective: " << bestObjective << "\n";
    summary << "increase: " << bestMetric.score - initial.score << "\n";
    summary << "support_mode: localized_bessel_parameter_vector\n";
    summary << "accepted: " << accepted << "/" << trials << "\n";
    summary << "mean_abs_pixel_delta: " << ds.meanAbs << "\n";
    summary << "max_abs_pixel_delta: " << ds.maxAbs << "\n";
    summary << "rms_pixel_delta: " << ds.rms << "\n";
    summary << "outputs: source.bmp updated.bmp delta.bmp delta_overlay.bmp source.ppm updated.ppm delta.ppm delta_overlay.ppm report.json update_trace.json support_dictionary.json\n";

    std::cout << "{\n";
    std::cout << "  \"backend\": \"cpp-localized-bessel-support-ffi/0.5.0\",\n";
    std::cout << "  \"outDir\": \"" << json_escape(outDir) << "\",\n";
    std::cout << "  \"initial_score\": " << round6(initial.score) << ",\n";
    std::cout << "  \"final_score\": " << round6(bestMetric.score) << ",\n";
    std::cout << "  \"final_objective\": " << round6(bestObjective) << ",\n";
    std::cout << "  \"increase\": " << round6(bestMetric.score - initial.score) << ",\n";
    std::cout << "  \"accepted\": " << accepted << ",\n";
    std::cout << "  \"mean_abs_pixel_delta\": " << round6(ds.meanAbs) << ",\n";
    std::cout << "  \"max_abs_pixel_delta\": " << round6(ds.maxAbs) << ",\n";
    std::cout << "  \"rms_pixel_delta\": " << round6(ds.rms) << "\n";
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
