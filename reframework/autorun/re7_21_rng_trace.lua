--[[
  RE7:21 RNG trace — Phase H (private research)
  Install: <RE7>/reframework/autorun/re7_21_rng_trace.lua
  Output:  <RE7>/reframework/data/re7_21_rng_trace.jsonl

  Controls:
    F9  — manual snapshot (stock + random state)
    F10 — dump CardGameMaster field names (discovery)
]]

local LOG_PATH = "reframework/data/re7_21_rng_trace.jsonl"
local TAG = "[RE7-21 RNG]"

local sdk_ok, sdk = pcall(require, "sdk")
if not sdk_ok then
    log.error(TAG .. " sdk module unavailable")
    return
end

local json_ok, json = pcall(require, "json")
if not json_ok then
    json = nil
end

-- ---------------------------------------------------------------------------
-- Logging
-- ---------------------------------------------------------------------------

local function append_log(obj)
    local line
    if json and json.dump then
        line = json.dump(obj)
    else
        -- minimal fallback
        line = string.format('{"event":"%s","t":%.3f}', tostring(obj.event or "?"), os.clock())
    end
    local f = io.open(LOG_PATH, "a")
    if f then
        f:write(line .. "\n")
        f:close()
    else
        log.warn(TAG .. " cannot write " .. LOG_PATH)
    end
end

local function log_event(event, fields)
    local row = { event = event, t = os.clock() }
    if fields then
        for k, v in pairs(fields) do
            row[k] = v
        end
    end
    append_log(row)
end

-- ---------------------------------------------------------------------------
-- Type / field discovery (names vary by dump — try candidates)
-- ---------------------------------------------------------------------------

local MASTER_SINGLETON = "app.CardGameMaster"
local RANDOM_TYPE = "UnityEngine.Random"

local STOCK_FIELD_CANDIDATES = {
    "StockCardList", "stockCardList", "_StockCardList", "mStockCardList",
}
local ROUND_FIELD_CANDIDATES = {
    "Round", "round", "_Round", "RoundNum", "roundNum",
}
local TRUMP_INDEX_CANDIDATES = {
    "RandomIndexList", "randomIndexList", "_RandomIndexList",
}

local function get_singleton(name)
    local ok, obj = pcall(function() return sdk.get_managed_singleton(name) end)
    if ok and obj then return obj end
    return nil
end

local function find_type(name)
    local ok, t = pcall(function() return sdk.find_type_definition(name) end)
    if ok and t then return t end
    return nil
end

local function read_field(obj, candidates)
    if not obj then return nil, nil end
    for _, name in ipairs(candidates) do
        local ok, field = pcall(function() return obj:get_field(name) end)
        if ok and field then
            local ok2, data = pcall(function() return field:get_data() end)
            if ok2 and data ~= nil then
                return name, data
            end
        end
    end
    return nil, nil
end

local function list_to_array(list_obj)
    local out = {}
    if not list_obj then return out end
    local ok_size, size = pcall(function() return list_obj:get_size() end)
    if not ok_size or not size then return out end
    for i = 0, size - 1 do
        local ok_el, el = pcall(function() return list_obj:get_element(i) end)
        if ok_el and el ~= nil then
            -- Card may be int, struct with CardNo, etc.
            local ok_num, num = pcall(function()
                if type(el) == "number" then return el end
                local f = el:get_field("CardNo") or el:get_field("cardNo") or el:get_field("No")
                if f then return f:get_data() end
                return tonumber(tostring(el))
            end)
            if ok_num and num then
                table.insert(out, num)
            else
                table.insert(out, tostring(el))
            end
        end
    end
    return out
end

-- ---------------------------------------------------------------------------
-- Unity Random state
-- ---------------------------------------------------------------------------

local random_type = find_type(RANDOM_TYPE)

local function read_random_state()
    if not random_type then
        return { available = false }
    end
    local state = { available = true }

    local ok_seed, seed_field = pcall(function() return random_type:get_field("seed") end)
    if ok_seed and seed_field then
        local ok_v, v = pcall(function() return seed_field:get_data(nil) end)
        if ok_v then state.seed = v end
    end

    local ok_st, st_get = pcall(function() return random_type:get_method("get_state") end)
    if ok_st and st_get then
        local ok_call, st = pcall(function() return st_get:call(nil) end)
        if ok_call and st then
            local parts = {}
            for _, fname in ipairs({ "s0", "s1", "s2", "s3", "S0", "S1", "S2", "S3" }) do
                local ok_f, f = pcall(function() return st:get_field(fname) end)
                if ok_f and f then
                    local ok_d, d = pcall(function() return f:get_data() end)
                    if ok_d then parts[fname] = d end
                end
            end
            if next(parts) then state.state_struct = parts end
        end
    end

    return state
end

-- ---------------------------------------------------------------------------
-- Snapshots
-- ---------------------------------------------------------------------------

local last_stock_key = nil
local last_round = nil

local function snapshot(reason)
    local master = get_singleton(MASTER_SINGLETON)
    if not master then
        log.warn(TAG .. " CardGameMaster not found — are you in 21?")
        log_event("snapshot_failed", { reason = reason, error = "no_singleton" })
        return
    end

    local stock_field, stock_raw = read_field(master, STOCK_FIELD_CANDIDATES)
    local round_field, round_val = read_field(master, ROUND_FIELD_CANDIDATES)
    local trump_field, trump_raw = read_field(master, TRUMP_INDEX_CANDIDATES)

    local stock = list_to_array(stock_raw)
    local trump_idx = list_to_array(trump_raw)

    local stock_key = table.concat(stock, ",")
    local round_changed = (round_val ~= nil and round_val ~= last_round)
    local stock_changed = (stock_key ~= "" and stock_key ~= last_stock_key)

    log_event("snapshot", {
        reason = reason,
        round = round_val,
        round_field = round_field,
        stock_field = stock_field,
        stock = stock,
        trump_index_field = trump_field,
        trump_index = trump_idx,
        random = read_random_state(),
        stock_changed = stock_changed,
        round_changed = round_changed,
    })

    if stock_changed then
        log_event("stock_shuffle", {
            round = round_val,
            stock = stock,
            random = read_random_state(),
        })
        last_stock_key = stock_key
    end

    if round_changed then
        log_event("round_start", {
            round = round_val,
            stock = stock,
            random = read_random_state(),
        })
        last_round = round_val
    end

    log.info(string.format("%s snapshot (%s) round=%s stock=[%s]", TAG, reason,
        tostring(round_val), table.concat(stock, ",")))
end

local function dump_master_fields()
    local master = get_singleton(MASTER_SINGLETON)
    if not master then
        log.warn(TAG .. " CardGameMaster not found")
        return
    end
    local ok, t = pcall(function() return master:get_type_definition() end)
    if not ok or not t then
        log.warn(TAG .. " cannot get type definition")
        return
    end
    log.info(TAG .. " --- CardGameMaster fields ---")
    local fields = {}
    local ok_f, flist = pcall(function() return t:get_fields() end)
    if ok_f and flist then
        for _, f in ipairs(flist) do
            local name = f:get_name()
            table.insert(fields, name)
            log.info(TAG .. "  field: " .. name)
        end
    end
    log_event("field_discovery", { fields = fields })
end

-- ---------------------------------------------------------------------------
-- Optional: hook Random.InitState
-- ---------------------------------------------------------------------------

local function try_hook_init_state()
    if not random_type then return end
    local ok_m, method = pcall(function() return random_type:get_method("InitState") end)
    if not ok_m or not method then return end

    sdk.hook(method,
        function(args)
            local seed = args[2] -- arg index varies; log raw args
            log_event("random_init_state", {
                seed = seed,
                random = read_random_state(),
            })
            log.info(TAG .. " InitState(" .. tostring(seed) .. ")")
        end,
        function(ret) end
    )
    log.info(TAG .. " hooked UnityEngine.Random.InitState")
end

-- ---------------------------------------------------------------------------
-- Lifecycle
-- ---------------------------------------------------------------------------

log.info(TAG .. " loaded — F9 snapshot, F10 field dump")
log_event("trace_start", { version = "1.0.0", master = MASTER_SINGLETON })

try_hook_init_state()

re.on_frame(function()
    -- light poll: auto-snapshot when round field readable (cheap check every 60f)
end)

re.on_draw_ui(function()
    if imgui.tree_node("RE7-21 RNG Trace") then
        imgui.text("Log: " .. LOG_PATH)
        if imgui.button("Snapshot (F9)") then snapshot("ui") end
        if imgui.button("Dump fields (F10)") then dump_master_fields() end
        imgui.tree_pop()
    end
end)

re.on_config_save(function(cfg)
    cfg.re7_21_rng_trace = cfg.re7_21_rng_trace or {}
end)

-- Key bindings (REFramework input API)
pcall(function()
    re.on_key_down(function(key)
        if key == 0x78 then snapshot("manual_f9") end      -- F9
        if key == 0x79 then dump_master_fields() end       -- F10
    end)
end)
