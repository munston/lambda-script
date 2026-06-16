#include <array>
#include <cstdio>
#include <cstdlib>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <sstream>
#include <string>
#include <vector>

#ifdef _WIN32
#define FORKS_POPEN _popen
#define FORKS_PCLOSE _pclose
#else
#define FORKS_POPEN popen
#define FORKS_PCLOSE pclose
#endif

namespace {

namespace fs = std::filesystem;

struct Args {
  std::vector<std::string> values;
};

struct SubprocessResult {
  int status = 1;
  std::string stdout_text;
};

struct GadgetTarget {
  std::string gizmo;
  std::string gadget;
  std::string integration_ref;
  std::string agent_branch_template;
};

struct RefProbe {
  std::string ref;
  bool exists = false;
  std::string head;
  std::string error;
};

struct AgentLane {
  std::string agent;
  std::string ref;
  bool exists = false;
  std::string head;
  std::string relation;
  int ahead = 0;
  int behind = 0;
  std::string error;
};

struct LatestWriter {
  std::string agent;
  std::string path;
  int sequence = 0;
  std::string created_at;
  std::string payload_path;
  std::string json_patch_sha256;
  std::string title;
  std::string op;
  std::string encoding;
  std::string content_sha256;
  int content_length = 0;
};

struct LedgerProbe {
  std::string agent;
  std::string ledger_path;
  bool ledger_exists = false;
  int entry_count = 0;
  int payload_count = 0;
  int payload_present = 0;
  int payload_missing = 0;
  std::vector<std::string> missing_payload_paths;
  std::vector<LatestWriter> latest_writers;
  std::string error;
};

struct ExpectedMutation {
  std::string scope;
  std::string ref;
  std::string mode;
};

struct CommandPlan {
  std::string command;
  std::string mutation_scope;
  bool mutates = false;
  GadgetTarget gadget;
  RefProbe integration;
  std::vector<AgentLane> lanes;
  std::vector<LedgerProbe> ledgers;
  std::vector<LatestWriter> latest_writers_by_path;
  std::vector<ExpectedMutation> expected_mutations;
};

const std::vector<std::string> kDefaultAgents = {"ed", "edd", "eddy", "guy"};

void print_usage() {
  std::cerr
    << "Usage:\n"
    << "  forks-core status [--gadget <gizmo> <gadget>]\n"
    << "  forks-core audit --gadget <gizmo> <gadget>\n";
}

std::string trim(std::string text) {
  while (!text.empty() && (text.back() == '\n' || text.back() == '\r' || text.back() == ' ' || text.back() == '\t')) text.pop_back();
  size_t start = 0;
  while (start < text.size() && (text[start] == ' ' || text[start] == '\t' || text[start] == '\n' || text[start] == '\r')) start++;
  return text.substr(start);
}

bool is_safe_name(const std::string& text) {
  if (text.empty()) return false;
  for (char ch : text) {
    const bool ok = (ch >= 'A' && ch <= 'Z') || (ch >= 'a' && ch <= 'z') || (ch >= '0' && ch <= '9') || ch == '_' || ch == '-';
    if (!ok) return false;
  }
  return true;
}

std::string json_escape(const std::string& text) {
  std::string out;
  for (char ch : text) {
    if (ch == '\\') out += "\\\\";
    else if (ch == '"') out += "\\\"";
    else if (ch == '\n') out += "\\n";
    else if (ch == '\r') out += "\\r";
    else if (ch == '\t') out += "\\t";
    else out += ch;
  }
  return out;
}

std::string json_string(const std::string& text) {
  return "\"" + json_escape(text) + "\"";
}

SubprocessResult run_readonly_command(const std::string& command) {
  SubprocessResult result;
  std::array<char, 256> buffer{};
  FILE* pipe = FORKS_POPEN(command.c_str(), "r");
  if (!pipe) {
    result.status = 1;
    return result;
  }
  while (fgets(buffer.data(), static_cast<int>(buffer.size()), pipe) != nullptr) {
    result.stdout_text += buffer.data();
  }
  result.status = FORKS_PCLOSE(pipe);
  result.stdout_text = trim(result.stdout_text);
  return result;
}

bool read_text_file(const std::string& path, std::string& out, std::string& error) {
  std::ifstream in(path, std::ios::binary);
  if (!in) {
    error = "file not readable";
    return false;
  }
  std::ostringstream buffer;
  buffer << in.rdbuf();
  out = buffer.str();
  return true;
}

int count_occurrences(const std::string& text, const std::string& needle) {
  int count = 0;
  size_t pos = 0;
  while (true) {
    pos = text.find(needle, pos);
    if (pos == std::string::npos) return count;
    count++;
    pos += needle.size();
  }
}

size_t find_matching_delimiter(const std::string& text, size_t start, char open_ch, char close_ch) {
  int depth = 0;
  bool in_string = false;
  bool escaped = false;
  for (size_t i = start; i < text.size(); ++i) {
    const char ch = text[i];
    if (in_string) {
      if (escaped) {
        escaped = false;
      } else if (ch == '\\') {
        escaped = true;
      } else if (ch == '"') {
        in_string = false;
      }
      continue;
    }
    if (ch == '"') {
      in_string = true;
      continue;
    }
    if (ch == open_ch) {
      depth++;
    } else if (ch == close_ch) {
      depth--;
      if (depth == 0) return i;
    }
  }
  return std::string::npos;
}

std::vector<std::string> extract_json_string_values(const std::string& text, const std::string& key) {
  std::vector<std::string> values;
  size_t pos = 0;
  const std::string quoted_key = "\"" + key + "\"";
  while (true) {
    pos = text.find(quoted_key, pos);
    if (pos == std::string::npos) return values;
    const size_t colon = text.find(':', pos + quoted_key.size());
    if (colon == std::string::npos) return values;
    const size_t first_quote = text.find('"', colon + 1);
    if (first_quote == std::string::npos) return values;
    std::string value;
    bool escaped = false;
    bool closed = false;
    for (size_t i = first_quote + 1; i < text.size(); ++i) {
      const char ch = text[i];
      if (escaped) {
        value.push_back(ch);
        escaped = false;
        continue;
      }
      if (ch == '\\') {
        escaped = true;
        continue;
      }
      if (ch == '"') {
        values.push_back(value);
        pos = i + 1;
        closed = true;
        break;
      }
      value.push_back(ch);
    }
    if (!closed) return values;
  }
}

std::string extract_json_string_value(const std::string& text, const std::string& key) {
  const std::vector<std::string> values = extract_json_string_values(text, key);
  if (values.empty()) return "";
  return values[0];
}

int extract_json_int_value(const std::string& text, const std::string& key) {
  const std::string quoted_key = "\"" + key + "\"";
  const size_t pos = text.find(quoted_key);
  if (pos == std::string::npos) return 0;
  const size_t colon = text.find(':', pos + quoted_key.size());
  if (colon == std::string::npos) return 0;
  size_t start = colon + 1;
  while (start < text.size() && (text[start] == ' ' || text[start] == '\n' || text[start] == '\r' || text[start] == '\t')) start++;
  size_t end = start;
  while (end < text.size() && text[end] >= '0' && text[end] <= '9') end++;
  if (end == start) return 0;
  return std::stoi(text.substr(start, end - start));
}

std::vector<std::string> extract_json_objects_in_array(const std::string& text, const std::string& key) {
  std::vector<std::string> objects;
  const std::string quoted_key = "\"" + key + "\"";
  const size_t key_pos = text.find(quoted_key);
  if (key_pos == std::string::npos) return objects;
  const size_t array_start = text.find('[', key_pos + quoted_key.size());
  if (array_start == std::string::npos) return objects;
  const size_t array_end = find_matching_delimiter(text, array_start, '[', ']');
  if (array_end == std::string::npos) return objects;
  size_t pos = array_start + 1;
  while (pos < array_end) {
    const size_t object_start = text.find('{', pos);
    if (object_start == std::string::npos || object_start > array_end) return objects;
    const size_t object_end = find_matching_delimiter(text, object_start, '{', '}');
    if (object_end == std::string::npos || object_end > array_end) return objects;
    objects.push_back(text.substr(object_start, object_end - object_start + 1));
    pos = object_end + 1;
  }
  return objects;
}

bool writer_is_newer_or_equal(const LatestWriter& candidate, const LatestWriter& current) {
  if (!candidate.created_at.empty() && !current.created_at.empty() && candidate.created_at != current.created_at) {
    return candidate.created_at > current.created_at;
  }
  return candidate.sequence >= current.sequence;
}

void upsert_latest_writer(std::vector<LatestWriter>& writers, const LatestWriter& candidate) {
  for (LatestWriter& writer : writers) {
    if (writer.path == candidate.path) {
      if (writer_is_newer_or_equal(candidate, writer)) writer = candidate;
      return;
    }
  }
  writers.push_back(candidate);
}

GadgetTarget make_gadget_target(const std::string& gizmo, const std::string& gadget) {
  GadgetTarget target;
  target.gizmo = gizmo;
  target.gadget = gadget;
  target.integration_ref = "origin/gadgets/" + gizmo + "/" + gadget + "/main";
  target.agent_branch_template = "origin/gadget-agents/" + gizmo + "/" + gadget + "/{agent}";
  return target;
}

std::string agent_ref(const GadgetTarget& target, const std::string& agent) {
  return "origin/gadget-agents/" + target.gizmo + "/" + target.gadget + "/" + agent;
}

std::string ledger_path(const GadgetTarget& target, const std::string& agent) {
  return "forks/replay-ledger/gadgets/" + target.gizmo + "/" + target.gadget + "/" + agent + ".json";
}

RefProbe probe_ref(const std::string& ref) {
  RefProbe probe;
  probe.ref = ref;
  const SubprocessResult result = run_readonly_command("git rev-parse --verify --quiet " + ref);
  if (result.status == 0 && !result.stdout_text.empty()) {
    probe.exists = true;
    probe.head = result.stdout_text;
  } else {
    probe.exists = false;
    probe.error = "ref not found";
  }
  return probe;
}

bool parse_two_counts(const std::string& text, int& left, int& right) {
  std::istringstream in(text);
  in >> left >> right;
  return !in.fail();
}

AgentLane inspect_agent_lane(const GadgetTarget& target, const RefProbe& integration, const std::string& agent) {
  AgentLane lane;
  lane.agent = agent;
  lane.ref = agent_ref(target, agent);
  const RefProbe lane_ref = probe_ref(lane.ref);
  lane.exists = lane_ref.exists;
  lane.head = lane_ref.head;
  if (!lane.exists) {
    lane.relation = "missing";
    lane.error = lane_ref.error;
    return lane;
  }
  if (!integration.exists) {
    lane.relation = "unknown";
    lane.error = "integration ref missing";
    return lane;
  }
  const SubprocessResult counts = run_readonly_command("git rev-list --left-right --count " + integration.ref + "..." + lane.ref);
  int behind = 0;
  int ahead = 0;
  if (counts.status != 0 || !parse_two_counts(counts.stdout_text, behind, ahead)) {
    lane.relation = "unknown";
    lane.error = "ahead/behind inspection failed";
    return lane;
  }
  lane.behind = behind;
  lane.ahead = ahead;
  if (ahead == 0 && behind == 0) lane.relation = "aligned";
  else if (ahead > 0 && behind == 0) lane.relation = "ahead-only";
  else if (ahead == 0 && behind > 0) lane.relation = "behind-only";
  else lane.relation = "diverged";
  return lane;
}

LedgerProbe inspect_replay_ledger(const GadgetTarget& target, const std::string& agent) {
  LedgerProbe probe;
  probe.agent = agent;
  probe.ledger_path = ledger_path(target, agent);
  if (!fs::exists(probe.ledger_path)) {
    probe.error = "ledger not found";
    return probe;
  }
  probe.ledger_exists = true;
  std::string text;
  if (!read_text_file(probe.ledger_path, text, probe.error)) return probe;
  const std::vector<std::string> entries = extract_json_objects_in_array(text, "entries");
  probe.entry_count = static_cast<int>(entries.size());
  for (const std::string& entry : entries) {
    const std::string payload = extract_json_string_value(entry, "payload_path");
    if (!payload.empty()) {
      probe.payload_count++;
      if (fs::exists(payload)) {
        probe.payload_present++;
      } else {
        probe.payload_missing++;
        probe.missing_payload_paths.push_back(payload);
      }
    }
    const int sequence = extract_json_int_value(entry, "sequence");
    const std::string created_at = extract_json_string_value(entry, "created_at");
    const std::string patch_hash = extract_json_string_value(entry, "json_patch_sha256");
    const std::string title = extract_json_string_value(entry, "title");
    const std::vector<std::string> fingerprints = extract_json_objects_in_array(entry, "file_fingerprints");
    for (const std::string& fingerprint : fingerprints) {
      LatestWriter writer;
      writer.agent = agent;
      writer.sequence = sequence;
      writer.created_at = created_at;
      writer.payload_path = payload;
      writer.json_patch_sha256 = patch_hash;
      writer.title = title;
      writer.path = extract_json_string_value(fingerprint, "path");
      writer.op = extract_json_string_value(fingerprint, "op");
      writer.encoding = extract_json_string_value(fingerprint, "encoding");
      writer.content_sha256 = extract_json_string_value(fingerprint, "content_sha256");
      writer.content_length = extract_json_int_value(fingerprint, "content_length");
      if (!writer.path.empty()) upsert_latest_writer(probe.latest_writers, writer);
    }
  }
  return probe;
}

bool parse_gadget_args(const Args& args, size_t start, GadgetTarget& target, std::string& error) {
  for (size_t i = start; i < args.values.size(); ++i) {
    if (args.values[i] == "--gadget" && i + 2 < args.values.size()) {
      const std::string gizmo = args.values[i + 1];
      const std::string gadget = args.values[i + 2];
      if (!is_safe_name(gizmo) || !is_safe_name(gadget)) {
        error = "gadget names must contain only letters, digits, underscore, or hyphen";
        return false;
      }
      target = make_gadget_target(gizmo, gadget);
      return true;
    }
  }
  error = "missing --gadget <gizmo> <gadget>";
  return false;
}

CommandPlan build_readonly_plan(const std::string& command, const GadgetTarget& target, bool include_ledgers) {
  CommandPlan plan;
  plan.command = command;
  plan.mutation_scope = "read-only";
  plan.mutates = false;
  plan.gadget = target;
  plan.integration = probe_ref(target.integration_ref);
  for (const std::string& agent : kDefaultAgents) {
    plan.lanes.push_back(inspect_agent_lane(target, plan.integration, agent));
    if (include_ledgers) {
      LedgerProbe ledger = inspect_replay_ledger(target, agent);
      for (const LatestWriter& writer : ledger.latest_writers) upsert_latest_writer(plan.latest_writers_by_path, writer);
      plan.ledgers.push_back(ledger);
    }
  }
  return plan;
}

void print_expected_mutations_empty() {
  std::cout << "  \"expected_mutations\": []\n";
}

void print_gadget(const GadgetTarget& target) {
  std::cout
    << "  \"gadget\": {\n"
    << "    \"gizmo\": " << json_string(target.gizmo) << ",\n"
    << "    \"gadget\": " << json_string(target.gadget) << ",\n"
    << "    \"integration_ref\": " << json_string(target.integration_ref) << ",\n"
    << "    \"agent_branch_template\": " << json_string(target.agent_branch_template) << "\n"
    << "  }";
}

void print_ref_probe(const std::string& key, const RefProbe& ref, bool trailing_comma) {
  std::cout
    << "  \"" << key << "\": {\n"
    << "    \"ref\": " << json_string(ref.ref) << ",\n"
    << "    \"exists\": " << (ref.exists ? "true" : "false") << ",\n"
    << "    \"head\": " << json_string(ref.head) << ",\n"
    << "    \"error\": " << json_string(ref.error) << "\n"
    << "  }" << (trailing_comma ? "," : "") << "\n";
}

void print_lanes(const std::vector<AgentLane>& lanes) {
  std::cout << "  \"agent_lanes\": [\n";
  for (size_t i = 0; i < lanes.size(); ++i) {
    const AgentLane& lane = lanes[i];
    std::cout
      << "    {\n"
      << "      \"agent\": " << json_string(lane.agent) << ",\n"
      << "      \"ref\": " << json_string(lane.ref) << ",\n"
      << "      \"exists\": " << (lane.exists ? "true" : "false") << ",\n"
      << "      \"head\": " << json_string(lane.head) << ",\n"
      << "      \"relation\": " << json_string(lane.relation) << ",\n"
      << "      \"ahead\": " << lane.ahead << ",\n"
      << "      \"behind\": " << lane.behind << ",\n"
      << "      \"error\": " << json_string(lane.error) << "\n"
      << "    }" << (i + 1 < lanes.size() ? "," : "") << "\n";
  }
  std::cout << "  ],\n";
}

void print_latest_writer(const LatestWriter& writer, const std::string& indent) {
  std::cout
    << indent << "{\n"
    << indent << "  \"agent\": " << json_string(writer.agent) << ",\n"
    << indent << "  \"path\": " << json_string(writer.path) << ",\n"
    << indent << "  \"sequence\": " << writer.sequence << ",\n"
    << indent << "  \"created_at\": " << json_string(writer.created_at) << ",\n"
    << indent << "  \"payload_path\": " << json_string(writer.payload_path) << ",\n"
    << indent << "  \"json_patch_sha256\": " << json_string(writer.json_patch_sha256) << ",\n"
    << indent << "  \"title\": " << json_string(writer.title) << ",\n"
    << indent << "  \"op\": " << json_string(writer.op) << ",\n"
    << indent << "  \"encoding\": " << json_string(writer.encoding) << ",\n"
    << indent << "  \"content_sha256\": " << json_string(writer.content_sha256) << ",\n"
    << indent << "  \"content_length\": " << writer.content_length << "\n"
    << indent << "}";
}

void print_missing_payloads(const std::vector<std::string>& paths) {
  std::cout << "      \"missing_payload_paths\": [\n";
  for (size_t i = 0; i < paths.size(); ++i) {
    std::cout << "        " << json_string(paths[i]) << (i + 1 < paths.size() ? "," : "") << "\n";
  }
  std::cout << "      ],\n";
}

void print_latest_writers_array(const std::string& key, const std::vector<LatestWriter>& writers, const std::string& item_indent) {
  std::cout << "  \"" << key << "\": [\n";
  for (size_t i = 0; i < writers.size(); ++i) {
    print_latest_writer(writers[i], item_indent);
    std::cout << (i + 1 < writers.size() ? "," : "") << "\n";
  }
  std::cout << "  ],\n";
}

void print_ledgers(const std::vector<LedgerProbe>& ledgers) {
  std::cout << "  \"replay_ledgers\": [\n";
  for (size_t i = 0; i < ledgers.size(); ++i) {
    const LedgerProbe& ledger = ledgers[i];
    std::cout
      << "    {\n"
      << "      \"agent\": " << json_string(ledger.agent) << ",\n"
      << "      \"ledger_path\": " << json_string(ledger.ledger_path) << ",\n"
      << "      \"ledger_exists\": " << (ledger.ledger_exists ? "true" : "false") << ",\n"
      << "      \"entry_count\": " << ledger.entry_count << ",\n"
      << "      \"payload_count\": " << ledger.payload_count << ",\n"
      << "      \"payload_present\": " << ledger.payload_present << ",\n"
      << "      \"payload_missing\": " << ledger.payload_missing << ",\n";
    print_missing_payloads(ledger.missing_payload_paths);
    std::cout << "      \"latest_writers\": [\n";
    for (size_t j = 0; j < ledger.latest_writers.size(); ++j) {
      print_latest_writer(ledger.latest_writers[j], "        ");
      std::cout << (j + 1 < ledger.latest_writers.size() ? "," : "") << "\n";
    }
    std::cout
      << "      ],\n"
      << "      \"error\": " << json_string(ledger.error) << "\n"
      << "    }" << (i + 1 < ledgers.size() ? "," : "") << "\n";
  }
  std::cout << "  ],\n";
}

void print_plan_json(const std::string& format, const CommandPlan& plan, const std::vector<std::string>& facts, bool include_ledgers) {
  std::cout
    << "{\n"
    << "  \"format\": " << json_string(format) << ",\n"
    << "  \"command\": " << json_string(plan.command) << ",\n"
    << "  \"mutation_scope\": " << json_string(plan.mutation_scope) << ",\n"
    << "  \"mutates\": " << (plan.mutates ? "true" : "false") << ",\n";
  print_gadget(plan.gadget);
  std::cout << ",\n";
  print_ref_probe("integration", plan.integration, true);
  print_lanes(plan.lanes);
  if (include_ledgers) {
    print_ledgers(plan.ledgers);
    print_latest_writers_array("latest_writers_by_path", plan.latest_writers_by_path, "    ");
  }
  std::cout << "  \"facts\": [\n";
  for (size_t i = 0; i < facts.size(); ++i) {
    std::cout << "    " << json_string(facts[i]) << (i + 1 < facts.size() ? "," : "") << "\n";
  }
  std::cout << "  ],\n";
  print_expected_mutations_empty();
  std::cout << "}\n";
}

int status_command(const Args& args) {
  GadgetTarget target;
  std::string error;
  if (!parse_gadget_args(args, 1, target, error)) {
    std::cout
      << "{\n"
      << "  \"format\": \"FORKS_CORE_STATUS_V4\",\n"
      << "  \"command\": \"status\",\n"
      << "  \"mutation_scope\": \"read-only\",\n"
      << "  \"mutates\": false,\n"
      << "  \"implemented\": true,\n"
      << "  \"requires_gadget_for_ref_inspection\": true,\n"
      << "  \"expected_mutations\": []\n"
      << "}\n";
    return 0;
  }
  const CommandPlan plan = build_readonly_plan("status", target, false);
  print_plan_json("FORKS_CORE_STATUS_V4", plan, {
    "integration_ref",
    "agent_refs",
    "ahead_behind",
    "expected_mutations"
  }, false);
  return 0;
}

int audit_command(const Args& args) {
  GadgetTarget target;
  std::string error;
  if (!parse_gadget_args(args, 1, target, error)) {
    std::cerr << "audit requires --gadget <gizmo> <gadget>\n";
    return 1;
  }
  const CommandPlan plan = build_readonly_plan("audit", target, true);
  print_plan_json("FORKS_CORE_AUDIT_V4", plan, {
    "integration_ref",
    "agent_refs",
    "ahead_behind",
    "ledger_file_presence",
    "payload_object_presence",
    "latest_writer_per_path",
    "expected_mutations"
  }, true);
  return 0;
}

} // namespace

int main(int argc, char** argv) {
  Args args;
  for (int i = 1; i < argc; ++i) args.values.push_back(argv[i]);
  if (args.values.empty()) {
    print_usage();
    return 1;
  }

  const std::string command = args.values[0];
  if (command == "status") return status_command(args);
  if (command == "audit") return audit_command(args);

  std::cerr << "unsupported forks-core command in read-only scaffold: " << command << "\n";
  print_usage();
  return 1;
}
