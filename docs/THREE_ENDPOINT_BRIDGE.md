# Three Endpoint Bridge

Minimal protocol-shaped scaffold for connecting three kinds of endpoints:

1. **Source** — LambdaScript source / program
2. **Host** — Host runtime (e.g. the environment executing the program)
3. **Foreign** — External / foreign interface (e.g. FFI, network, other runtimes)

This initial version defines only types and a basic routing stub. The goal is to establish a clear protocol shape that can later be implemented in LambdaScript itself.

## Endpoints

- `source`: LambdaScript code / modules
- `host`: The runtime hosting and executing LambdaScript
- `foreign`: External systems accessed via FFI, IPC, network, etc.

## Future Direction

- Message routing between any pair of endpoints
- Capability negotiation
- Serialization / protocol boundaries
- Eventual reimplementation of core bridge logic in LambdaScript
