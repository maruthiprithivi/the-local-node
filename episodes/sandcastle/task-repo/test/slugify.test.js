import assert from "node:assert/strict";
import { test } from "node:test";
import { slugify } from "../src/slugify.js";

test("lowercases and hyphenates spaces", () => {
  assert.equal(slugify("Hello World"), "hello-world");
});

test("trims and collapses whitespace", () => {
  assert.equal(slugify("  Foo   Bar  "), "foo-bar");
});

test("strips punctuation and collapses hyphens", () => {
  assert.equal(slugify("Hello, World!!"), "hello-world");
  assert.equal(slugify("already--hyphenated"), "already-hyphenated");
});

test("strips leading and trailing hyphens", () => {
  assert.equal(slugify("---Hello---"), "hello");
});

test("empty or punctuation-only input becomes n-a", () => {
  assert.equal(slugify(""), "n-a");
  assert.equal(slugify("   "), "n-a");
  assert.equal(slugify("!!!"), "n-a");
});
