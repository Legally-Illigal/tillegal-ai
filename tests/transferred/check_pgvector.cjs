// Optional PostgreSQL-in-WASM test. All tables live only in this process.
const fs = require("node:fs");
const path = require("node:path");
const {createRequire} = require("node:module");
const packages = createRequire(path.resolve(process.env.PGLITE_TEST_PREFIX, "package.json"));
const {PGlite} = packages("@electric-sql/pglite");
const {vector} = packages("@electric-sql/pglite-pgvector");

async function main() {
    const [source, parsed, profile, windows] = JSON.parse(fs.readFileSync(0, "utf8"));
    const db = new PGlite({extensions: {vector}});
    try {
        await db.exec("create role anon; create role authenticated; create role service_role bypassrls; create schema extensions");
        await db.exec("alter default privileges in schema public grant select,insert,update,delete on tables to service_role");
        const migrations = path.join(__dirname, "../../src/integrations/database/supabase/migrations");
        for (const file of fs.readdirSync(migrations).filter(x => x.endsWith(".sql")).sort()) {
            console.error("Migration",file);
            await db.exec(fs.readFileSync(path.join(migrations, file), "utf8"));
        }
        await db.exec("insert into dense_indexes(index_name,provider,model_name,status) values ('legacy','fixture','legacy-1536','READY')");
        const allowed = await db.query("select has_function_privilege('anon','public.read_staging_version(text,jsonb)','execute') as ok");
        if (allowed.rows[0].ok) throw Error("anon has unexpected access");
        await db.exec("set role service_role");
        const save = "select public.save_staging_version($1::jsonb,$2::jsonb,$3::jsonb,$4::jsonb) as vid";
        const read = "select public.read_staging_version($1,$2::jsonb) as record";
        const args = [source,parsed,profile,windows].map(x => JSON.stringify(x));
        console.error("Round trip");
        const vid = (await db.query(save,args)).rows[0].vid;
        console.error("Replay");
        await db.query(save,args);
        const bad = structuredClone(windows);
        bad[0].chunk_id = "missing";
        let rejected = false;
        try { await db.query(save,[...args.slice(0,3), JSON.stringify(bad)]); }
        catch { rejected = true; }
        if (!rejected) throw Error("Expected rejected bad reference");
        console.error("Read back");
        const other = await db.query(read,[vid, JSON.stringify({...profile,revision:"other"})]);
        if (other.rows[0].record !== null) throw Error("Profile isolation failed");
        const result = await db.query(read,[vid,JSON.stringify(profile)]);
        const legacy = await db.query("select status,embedding_dimension from dense_indexes where index_name='legacy'");
        if (legacy.rows[0].status !== "READY" || legacy.rows[0].embedding_dimension !== 1536)
            throw Error("Legacy index was changed");
        process.stdout.write(JSON.stringify(result.rows[0].record));
    } catch (e) { console.error("SQL failure:",e.message,e.where||""); throw e; } finally { await db.close(); }
}
main().catch(e => { console.error(e.stack); process.exitCode = 1; });
