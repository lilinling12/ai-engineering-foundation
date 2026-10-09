import test from "node:test";
import assert from "node:assert/strict";
import { health } from "../dist/index.js";
test("health is stable", () => assert.deepEqual(health(), { status: "ok" }));
