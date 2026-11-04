// Project-owned checks for the few Next/React rules without native Oxlint ports.
// Uses the locked TypeScript parser; no ESLint or glob implementation is loaded.
import ts from "typescript";
import { readdirSync, readFileSync } from "node:fs";
import { resolve, relative } from "node:path";
import { fileURLToPath } from "node:url";

const deprecated = {
  react: new Set(["renderComponent", "renderComponentToString", "renderComponentToStaticMarkup",
    "isValidComponent", "isValidClass", "render", "unmountComponentAtNode", "findDOMNode",
    "renderToString", "renderToStaticMarkup", "createClass", "PropTypes", "DOM",
    "addons.classSet", "addons.cloneWithProps", "addons.LinkedStateMixin", "addons.TestUtils"]),
  "react-dom": new Set(["render", "hydrate", "unmountComponentAtNode", "findDOMNode"]),
  "react-dom/server": new Set(["renderToNodeStream"]),
  "react-addons-perf": new Set(["printDOM", "getMeasurementsSummaryMap"]),
};
const lifecycles = new Set(["componentWillMount", "componentWillReceiveProps", "componentWillUpdate"]);

function parts(node) {
  if (ts.isIdentifier(node)) return [node.text];
  if (node.kind === ts.SyntaxKind.ThisKeyword) return ["this"];
  if (ts.isPropertyAccessExpression(node)) return [...parts(node.expression), node.name.text];
  if (ts.isElementAccessExpression(node) && ts.isStringLiteralLike(node.argumentExpression))
    return [...parts(node.expression), node.argumentExpression.text];
  return [];
}

export function inspect(text, filename) {
  const source = ts.createSourceFile(filename, text, ts.ScriptTarget.Latest, true);
  const aliases = new Map([["React", ["react", ""]], ["ReactDOM", ["react-dom", ""]],
    ["ReactDOMServer", ["react-dom/server", ""]], ["ReactPerf", ["react-addons-perf", ""]],
    ["Perf", ["react-addons-perf", ""]]]);
  const findings = [];
  const report = (node, rule, severity) => findings.push({ rule, severity,
    line: source.getLineAndCharacterOfPosition(node.getStart(source)).line + 1 });
  for (const node of source.statements) {
    if (!ts.isImportDeclaration(node) || !ts.isStringLiteral(node.moduleSpecifier)) continue;
    const moduleName = node.moduleSpecifier.text;
    if (!(moduleName in deprecated)) continue;
    const clause = node.importClause;
    if (clause?.name) aliases.set(clause.name.text, [moduleName, ""]);
    const bindings = clause?.namedBindings;
    if (bindings && ts.isNamespaceImport(bindings)) aliases.set(bindings.name.text, [moduleName, ""]);
    if (bindings && ts.isNamedImports(bindings)) for (const item of bindings.elements) {
      const member = (item.propertyName ?? item.name).text;
      aliases.set(item.name.text, [moduleName, member]);
      if (deprecated[moduleName].has(member)) report(item, "react/no-deprecated", "error");
    }
  }
  function visit(node) {
    if (ts.isPropertyAccessExpression(node) || ts.isElementAccessExpression(node)) {
      const [base, ...members] = parts(node);
      const alias = aliases.get(base);
      if (alias && deprecated[alias[0]].has([alias[1], ...members].filter(Boolean).join(".")))
        report(node, "react/no-deprecated", "error");
      if (base === "this" && members[0] === "transferPropsTo") report(node, "react/no-deprecated", "error");
    }
    // Legacy lifecycle names are reserved in this React application, including object components.
    if ((ts.isMethodDeclaration(node) || ts.isPropertyDeclaration(node) || ts.isPropertyAssignment(node)) &&
        node.name && lifecycles.has(node.name.getText(source).replace(/["']/g, "")))
      report(node, "react/no-deprecated", "error");
    let target, value;
    if (ts.isCallExpression(node) && parts(node.expression).at(-1) === "assign") {
      target = parts(node.expression).slice(0, -1); value = node.arguments[0];
    }
    if (ts.isBinaryExpression(node) && node.operatorToken.kind === ts.SyntaxKind.EqualsToken &&
        parts(node.left).at(-1) === "href") {
      target = parts(node.left).slice(0, -1); value = node.right;
    }
    if (target && ["location", "window.location", "globalThis.location", "document.location", "self.location"].includes(target.join(".")) && value) {
      const prefix = ts.isStringLiteralLike(value) ? value.text : ts.isTemplateExpression(value) ? value.head.text : null;
      if (prefix !== null && !/^(?:[a-z][\d+.a-z-]*:|\/\/)/i.test(prefix))
        report(node, "next/no-location-assign-relative-destination", "warning");
    }
    // No compiler configuration was supplied to the former hooks rules. Fail closed
    // on introducing one until its config/gating validation is integrated and tested.
    if (/(?:next|babel)\.config\.|\.babelrc|package\.json$/.test(filename) &&
        (ts.isIdentifier(node) && node.text === "reactCompiler" ||
        ts.isStringLiteralLike(node) && (node.text === "reactCompiler" ||
          node.text.includes("babel-plugin-react-compiler"))))
      report(node, "react/compiler-configuration-review", "error");
    ts.forEachChild(node, visit);
  }
  visit(source);
  return findings;
}

export function sourceFiles(root) {
  return readdirSync(root, { withFileTypes: true }).flatMap(entry => {
    if (["node_modules", ".next", "out", "build", ".git"].includes(entry.name)) return [];
    const path = resolve(root, entry.name);
    if (entry.isDirectory()) return sourceFiles(path);
    return (/\.(?:[cm]?[jt]sx?)$/.test(entry.name) && entry.name !== "next-env.d.ts") ||
      /^(?:package\.json|\.babelrc(?:\..*)?|babel\.config\..*)$/.test(entry.name) ? [path] : [];
  });
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const root = resolve(fileURLToPath(new URL("..", import.meta.url)));
  let errors = 0;
  for (const file of sourceFiles(root)) {
    for (const finding of inspect(readFileSync(file, "utf8"), file)) {
      console.log(`${relative(root, file)}:${finding.line}: ${finding.severity} ${finding.rule}`);
      errors += Number(finding.severity === "error");
    }
  }
  process.exitCode = errors ? 1 : 0;
}
