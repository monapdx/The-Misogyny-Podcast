```js-engine-debug
// ============================================================
// FRONTMATTER NORMALIZER
// Obsidian + JS Engine
//
// SAFE DEFAULT:
// DRY_RUN = true
//
// Change DRY_RUN to false ONLY after reviewing the report.
// ============================================================

const DRY_RUN = true;

// Optional: limit processing to one folder.
// "" = entire vault.
const FOLDER = "";

// Report gets written here.
const REPORT_PATH = "Frontmatter Normalization Report.md";


// ============================================================
// SCHEMA
// Add/change rules here.
// ============================================================

const SCHEMA = {
    created: {
        aliases: [
            "date-created",
            "date_created",
            "creation-date",
            "creation_date",
            "created_at",
            "dateCreated"
        ],
        type: "date"
    },

    modified: {
        aliases: [
            "date-modified",
            "date_modified",
            "modified_at",
            "updated",
            "updated_at",
            "last-modified",
            "last_modified"
        ],
        type: "date"
    },

    tags: {
        aliases: [
            "tag",
            "keywords",
            "labels"
        ],
        type: "list"
    },

    aliases: {
        aliases: [
            "alias",
            "aka"
        ],
        type: "list"
    },

    status: {
        aliases: [
            "state",
            "project-status",
            "project_status"
        ],

        type: "enum",

        values: {
            "active": "active",
            "in progress": "active",
            "in-progress": "active",
            "in_progress": "active",
            "wip": "active",
            "working": "active",

            "done": "complete",
            "finished": "complete",
            "completed": "complete",
            "complete": "complete",

            "paused": "paused",
            "on hold": "paused",
            "on-hold": "paused",
            "hold": "paused",

            "cancelled": "cancelled",
            "canceled": "cancelled",
            "abandoned": "cancelled",

            "archived": "archived",
            "archive": "archived"
        }
    }
};


// ============================================================
// OPTIONS
// ============================================================

// Never automatically resolve a note containing BOTH:
//
// created: ...
// date-created: ...
//
// Those become conflicts requiring manual review.
const SKIP_CONFLICTS = true;


// Don't touch Obsidian's built-in-ish / special properties here
// if we don't explicitly recognize them.
const IGNORE_PROPERTIES = new Set([
    "cssclasses",
    "publish",
    "permalink"
]);


// ============================================================
// HELPERS
// ============================================================

function cleanKey(key) {
    return String(key).trim();
}


function canonicalLookup() {
    const lookup = new Map();

    for (const [canonical, config] of Object.entries(SCHEMA)) {
        lookup.set(canonical.toLowerCase(), canonical);

        for (const alias of config.aliases ?? []) {
            lookup.set(alias.toLowerCase(), canonical);
        }
    }

    return lookup;
}


const KEY_LOOKUP = canonicalLookup();


function getCanonicalKey(key) {
    return KEY_LOOKUP.get(String(key).toLowerCase()) ?? null;
}


// ------------------------------------------------------------
// Date normalization
// ------------------------------------------------------------

function normalizeDate(value) {

    if (value == null || value === "") {
        return value;
    }

    // YAML parser may already have made it a Date.
    if (value instanceof Date && !isNaN(value)) {
        return value.toISOString().slice(0, 10);
    }

    let str = String(value).trim();

    // Already ISO date.
    if (/^\d{4}-\d{2}-\d{2}$/.test(str)) {
        return str;
    }

    // ISO datetime:
    // 2026-08-31T14:32:00
    if (/^\d{4}-\d{2}-\d{2}T/.test(str)) {
        return str.slice(0, 10);
    }

    // M/D/YYYY or MM/DD/YYYY
    let match = str.match(
        /^(\d{1,2})\/(\d{1,2})\/(\d{4})$/
    );

    if (match) {
        const [, month, day, year] = match;

        return [
            year,
            month.padStart(2, "0"),
            day.padStart(2, "0")
        ].join("-");
    }

    // M-D-YYYY
    match = str.match(
        /^(\d{1,2})-(\d{1,2})-(\d{4})$/
    );

    if (match) {
        const [, month, day, year] = match;

        return [
            year,
            month.padStart(2, "0"),
            day.padStart(2, "0")
        ].join("-");
    }

    // YYYY/MM/DD
    match = str.match(
        /^(\d{4})\/(\d{1,2})\/(\d{1,2})$/
    );

    if (match) {
        const [, year, month, day] = match;

        return [
            year,
            month.padStart(2, "0"),
            day.padStart(2, "0")
        ].join("-");
    }

    // Ambiguous/unrecognized dates are preserved.
    return value;
}


// ------------------------------------------------------------
// List normalization
// ------------------------------------------------------------

function normalizeList(value) {

    if (value == null) {
        return value;
    }

    if (Array.isArray(value)) {
        return [
            ...new Set(
                value
                    .map(v => String(v).trim())
                    .filter(Boolean)
            )
        ];
    }

    if (typeof value === "string") {

        const str = value.trim();

        if (!str) {
            return [];
        }

        // Convert comma-delimited lists.
        if (str.includes(",")) {
            return [
                ...new Set(
                    str
                        .split(",")
                        .map(v => v.trim())
                        .filter(Boolean)
                )
            ];
        }

        // One value becomes a one-item YAML list.
        return [str];
    }

    return value;
}


// ------------------------------------------------------------
// Enum normalization
// ------------------------------------------------------------

function normalizeEnum(value, config) {

    if (value == null) {
        return value;
    }

    const str = String(value).trim();

    const lookupValue = str.toLowerCase();

    return config.values?.[lookupValue] ?? value;
}


// ------------------------------------------------------------
// Generic value normalizer
// ------------------------------------------------------------

function normalizeValue(value, config) {

    switch (config.type) {

        case "date":
            return normalizeDate(value);

        case "list":
            return normalizeList(value);

        case "enum":
            return normalizeEnum(value, config);

        default:
            return value;
    }
}


// ------------------------------------------------------------
// Compare arrays / values sanely
// ------------------------------------------------------------

function valuesEqual(a, b) {
    return JSON.stringify(a) === JSON.stringify(b);
}


// ============================================================
// COLLECT FILES
// ============================================================

let files = app.vault.getMarkdownFiles();

if (FOLDER) {
    const prefix = FOLDER.endsWith("/")
        ? FOLDER
        : FOLDER + "/";

    files = files.filter(file =>
        file.path.startsWith(prefix)
    );
}


// Don't process the report itself.
files = files.filter(
    file => file.path !== REPORT_PATH
);


// ============================================================
// REPORT DATA
// ============================================================

const stats = {
    scanned: 0,
    hasFrontmatter: 0,
    unchanged: 0,
    wouldChange: 0,
    changed: 0
};


const propertyCounts = new Map();

const renameCounts = new Map();

const valueChangeCounts = new Map();

const conflicts = [];

const unknownProperties = new Map();

const changedFiles = [];


// ============================================================
// SCAN
// ============================================================

for (const file of files) {

    stats.scanned++;

    const cache =
        app.metadataCache.getFileCache(file);

    const frontmatter =
        cache?.frontmatter;

    if (!frontmatter) {
        stats.unchanged++;
        continue;
    }

    stats.hasFrontmatter++;

    // Obsidian metadata includes some internal keys
    // beginning with "position".
    const keys = Object.keys(frontmatter)
        .filter(key => key !== "position");

    // Property inventory.
    for (const key of keys) {

        propertyCounts.set(
            key,
            (propertyCounts.get(key) ?? 0) + 1
        );

        const canonical =
            getCanonicalKey(key);

        if (
            !canonical &&
            !IGNORE_PROPERTIES.has(key)
        ) {
            unknownProperties.set(
                key,
                (unknownProperties.get(key) ?? 0) + 1
            );
        }
    }


    const changes = [];
    const fileConflicts = [];


    // --------------------------------------------------------
    // Detect alias renames
    // --------------------------------------------------------

    for (const key of keys) {

        const canonical =
            getCanonicalKey(key);

        if (!canonical) {
            continue;
        }

        const config =
            SCHEMA[canonical];

        const sourceValue =
            frontmatter[key];


        // Alias exists but canonical also exists.
        if (
            key !== canonical &&
            Object.prototype.hasOwnProperty.call(
                frontmatter,
                canonical
            )
        ) {

            fileConflicts.push({
                canonical,
                alias: key,
                canonicalValue:
                    frontmatter[canonical],
                aliasValue:
                    sourceValue
            });

            continue;
        }


        // Rename alias -> canonical.
        if (key !== canonical) {

            changes.push({
                type: "rename",
                from: key,
                to: canonical,
                oldValue: sourceValue,
                newValue:
                    normalizeValue(
                        sourceValue,
                        config
                    )
            });

            const rename =
                `${key} → ${canonical}`;

            renameCounts.set(
                rename,
                (renameCounts.get(rename) ?? 0) + 1
            );

            continue;
        }


        // Canonical property: normalize value.
        const normalized =
            normalizeValue(
                sourceValue,
                config
            );

        if (
            !valuesEqual(
                sourceValue,
                normalized
            )
        ) {

            changes.push({
                type: "value",
                key: canonical,
                oldValue: sourceValue,
                newValue: normalized
            });

            const description =
                `${canonical}: ${JSON.stringify(sourceValue)} → ${JSON.stringify(normalized)}`;

            valueChangeCounts.set(
                description,
                (valueChangeCounts.get(description) ?? 0) + 1
            );
        }
    }


    // --------------------------------------------------------
    // Save conflicts
    // --------------------------------------------------------

    if (fileConflicts.length) {

        conflicts.push({
            file: file.path,
            conflicts: fileConflicts
        });
    }


    // Skip entire file if conflict exists.
    if (
        SKIP_CONFLICTS &&
        fileConflicts.length
    ) {
        continue;
    }


    if (!changes.length) {
        stats.unchanged++;
        continue;
    }


    stats.wouldChange++;

    changedFiles.push({
        file: file.path,
        changes
    });


    // --------------------------------------------------------
    // ACTUAL WRITE
    // --------------------------------------------------------

    if (!DRY_RUN) {

        await app.fileManager.processFrontMatter(
            file,
            fm => {

                for (const change of changes) {

                    if (change.type === "rename") {

                        // Safety check:
                        // don't overwrite canonical values.
                        if (
                            Object.prototype.hasOwnProperty.call(
                                fm,
                                change.to
                            )
                        ) {
                            continue;
                        }

                        fm[change.to] =
                            change.newValue;

                        delete fm[change.from];
                    }


                    if (change.type === "value") {

                        fm[change.key] =
                            change.newValue;
                    }
                }
            }
        );

        stats.changed++;
    }
}


// ============================================================
// REPORT GENERATION
// ============================================================

function sortMap(map) {
    return [...map.entries()]
        .sort((a, b) => b[1] - a[1]);
}


function mdValue(value) {

    if (Array.isArray(value)) {
        return "`" +
            JSON.stringify(value) +
            "`";
    }

    if (typeof value === "object") {
        return "`" +
            JSON.stringify(value) +
            "`";
    }

    return "`" +
        String(value) +
        "`";
}


let report = `# Frontmatter Normalization Report

> Generated: ${new Date().toLocaleString()}

**Mode:** ${
    DRY_RUN
        ? "🟡 DRY RUN — nothing was modified"
        : "🟢 LIVE — changes were applied"
}

---

## Summary

| Item | Count |
|---|---:|
| Markdown files scanned | ${stats.scanned} |
| Files with frontmatter | ${stats.hasFrontmatter} |
| Files unchanged | ${stats.unchanged} |
| Files that would change | ${stats.wouldChange} |
| Files actually changed | ${stats.changed} |
| Files with conflicts | ${conflicts.length} |
| Distinct unknown properties | ${unknownProperties.size} |

`;


// ============================================================
// PROPERTY INVENTORY
// ============================================================

report += `
## Property Inventory

| Property | Notes |
|---|---:|
`;

for (const [key, count]
    of sortMap(propertyCounts)) {

    report +=
        `| \`${key}\` | ${count} |\n`;
}


// ============================================================
// RENAMES
// ============================================================

report += `
## Property Renames

`;

if (!renameCounts.size) {

    report +=
        "_No property aliases detected._\n";

} else {

    report +=
        "| Rename | Notes |\n" +
        "|---|---:|\n";

    for (const [rename, count]
        of sortMap(renameCounts)) {

        report +=
            `| \`${rename}\` | ${count} |\n`;
    }
}


// ============================================================
// UNKNOWN PROPERTIES
// ============================================================

report += `
## Unknown Properties

These properties are **not modified**. They are listed so you can decide whether they belong in the schema.

`;

if (!unknownProperties.size) {

    report +=
        "_No unknown properties found._\n";

} else {

    report +=
        "| Property | Notes |\n" +
        "|---|---:|\n";

    for (const [key, count]
        of sortMap(unknownProperties)) {

        report +=
            `| \`${key}\` | ${count} |\n`;
    }
}


// ============================================================
// CONFLICTS
// ============================================================

report += `
## ⚠️ Conflicts Requiring Review

A conflict means both the canonical property and one of its aliases exist in the same note.

**No automatic change was made to these properties.**

`;

if (!conflicts.length) {

    report +=
        "_No conflicts found._\n";

} else {

    for (const entry of conflicts) {

        report +=
            `### [[${entry.file.replace(/\.md$/, "")}]]\n\n`;

        for (const conflict
            of entry.conflicts) {

            report +=
`- Canonical: \`${conflict.canonical}\` = ${mdValue(conflict.canonicalValue)}
- Alias: \`${conflict.alias}\` = ${mdValue(conflict.aliasValue)}

`;
        }
    }
}


// ============================================================
// FILE CHANGES
// ============================================================

report += `
## Files ${
    DRY_RUN
        ? "That Would Change"
        : "Changed"
}

`;

if (!changedFiles.length) {

    report +=
        "_Nothing to normalize._\n";

} else {

    for (const entry
        of changedFiles) {

        report +=
            `### [[${entry.file.replace(/\.md$/, "")}]]\n\n`;

        for (const change
            of entry.changes) {

            if (change.type === "rename") {

                report +=
`- Rename \`${change.from}\` → \`${change.to}\`
  - ${mdValue(change.oldValue)} → ${mdValue(change.newValue)}
`;

            } else {

                report +=
`- Normalize \`${change.key}\`
  - ${mdValue(change.oldValue)} → ${mdValue(change.newValue)}
`;
            }
        }

        report += "\n";
    }
}


// ============================================================
// WRITE REPORT
// ============================================================

const existing =
    app.vault.getAbstractFileByPath(
        REPORT_PATH
    );

if (existing) {

    await app.vault.modify(
        existing,
        report
    );

} else {

    await app.vault.create(
        REPORT_PATH,
        report
    );
}


// ============================================================
// RETURN RESULT TO JS ENGINE
// ============================================================

return engine.markdown.create(`
# Frontmatter Normalizer

${DRY_RUN
    ? "🟡 **Dry run complete. No notes were modified.**"
    : "🟢 **Normalization complete.**"
}

- **Scanned:** ${stats.scanned}
- **Would change:** ${stats.wouldChange}
- **Changed:** ${stats.changed}
- **Conflicts:** ${conflicts.length}
- **Unknown properties:** ${unknownProperties.size}

Full results: [[${REPORT_PATH.replace(/\.md$/, "")}]]

${DRY_RUN
    ? "Review the report before changing \`DRY_RUN\` to \`false\`."
    : ""
}
`);
```