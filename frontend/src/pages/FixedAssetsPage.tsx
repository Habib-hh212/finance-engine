import { useEffect, useState } from "react";
import {
  Alert,
  Button,
  Card,
  CardContent,
  Chip,
  IconButton,
  MenuItem,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TextField,
  Typography,
} from "@mui/material";
import SwapHorizIcon from "@mui/icons-material/SwapHoriz";
import DeleteForeverIcon from "@mui/icons-material/DeleteForever";
import CloseIcon from "@mui/icons-material/Close";
import { useCompany } from "../context/CompanyContext";
import { listCostCenters, listGLAccounts } from "../api/budgets";
import {
  createAsset,
  createAssetClass,
  disposeAsset,
  getAssetRegister,
  listAssetClasses,
  listAssets,
  runDepreciation,
  transferAsset,
} from "../api/fixedAssets";
import type { Asset, AssetClass, AssetRegister, CostCenter, DepreciationMethod, DepreciationRun, DisposalType, GLAccount } from "../api/types";

function todayValue() {
  return new Date().toISOString().slice(0, 10);
}

const fmt = (v: number) => v.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });

const METHOD_LABEL: Record<DepreciationMethod, string> = {
  straight_line: "Straight-Line",
  declining_balance: "Declining Balance",
  sum_of_years_digits: "Sum-of-Years-Digits",
};

const STATUS_COLOR: Record<string, "success" | "warning" | "default" | "error"> = {
  active: "success",
  sold: "default",
  scrapped: "warning",
  lost: "error",
};

export function FixedAssetsPage() {
  const { company } = useCompany();
  const [glAccounts, setGlAccounts] = useState<GLAccount[]>([]);
  const [costCenters, setCostCenters] = useState<CostCenter[]>([]);
  const [assetClasses, setAssetClasses] = useState<AssetClass[]>([]);
  const [assets, setAssets] = useState<Asset[]>([]);
  const [register, setRegister] = useState<AssetRegister | null>(null);
  const [registerAsOf, setRegisterAsOf] = useState(todayValue());
  const [error, setError] = useState<string | null>(null);

  // New asset class form
  const [className, setClassName] = useState("");
  const [apcAccount, setApcAccount] = useState("");
  const [depExpenseAccount, setDepExpenseAccount] = useState("");
  const [accumDepAccount, setAccumDepAccount] = useState("");
  const [gainAccount, setGainAccount] = useState("");
  const [lossAccount, setLossAccount] = useState("");
  const [defaultMethod, setDefaultMethod] = useState<DepreciationMethod>("straight_line");
  const [defaultLife, setDefaultLife] = useState("5");
  const [defaultFactor, setDefaultFactor] = useState("2");

  // New asset (acquisition) form
  const [assetClassId, setAssetClassId] = useState("");
  const [code, setCode] = useState("");
  const [name, setName] = useState("");
  const [acqDate, setAcqDate] = useState(todayValue());
  const [cost, setCost] = useState("");
  const [salvage, setSalvage] = useState("0");
  const [lifeOverride, setLifeOverride] = useState("");
  const [methodOverride, setMethodOverride] = useState<DepreciationMethod | "">("");
  const [fundingAccount, setFundingAccount] = useState("");
  const [assetCostCenter, setAssetCostCenter] = useState("");

  // Depreciation run
  const [runPeriod, setRunPeriod] = useState(todayValue().slice(0, 7) + "-01");
  const [runResult, setRunResult] = useState<DepreciationRun | null>(null);

  // Transfer / dispose panel
  const [manageAsset, setManageAsset] = useState<Asset | null>(null);
  const [manageMode, setManageMode] = useState<"transfer" | "dispose" | null>(null);
  const [transferCostCenter, setTransferCostCenter] = useState("");
  const [disposalType, setDisposalType] = useState<DisposalType>("sale");
  const [disposalDate, setDisposalDate] = useState(todayValue());
  const [proceeds, setProceeds] = useState("0");
  const [proceedsAccount, setProceedsAccount] = useState("");
  const [disposalReason, setDisposalReason] = useState("");

  const load = async () => {
    if (!company) return;
    setError(null);
    try {
      const [accounts, centers, classes, assetList] = await Promise.all([
        listGLAccounts(company.id),
        listCostCenters(company.id),
        listAssetClasses(company.id),
        listAssets(company.id),
      ]);
      setGlAccounts(accounts);
      setCostCenters(centers);
      setAssetClasses(classes);
      setAssets(assetList);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load fixed assets");
    }
  };

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [company?.id]);

  const loadRegister = async () => {
    if (!company) return;
    try {
      setRegister(await getAssetRegister(company.id, registerAsOf));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load the asset register");
    }
  };

  useEffect(() => {
    loadRegister();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [company?.id, registerAsOf, assets]);

  const handleCreateClass = async () => {
    if (!company || !className || !apcAccount || !depExpenseAccount || !accumDepAccount || !gainAccount || !lossAccount) return;
    setError(null);
    try {
      await createAssetClass(
        company.id,
        className,
        apcAccount,
        depExpenseAccount,
        accumDepAccount,
        gainAccount,
        lossAccount,
        defaultMethod,
        Number(defaultLife) || 5,
        Number(defaultFactor) || 2,
      );
      setClassName("");
      setApcAccount("");
      setDepExpenseAccount("");
      setAccumDepAccount("");
      setGainAccount("");
      setLossAccount("");
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create the asset class");
    }
  };

  const handleAcquire = async () => {
    if (!company || !assetClassId || !code || !name || !cost || !fundingAccount) return;
    setError(null);
    try {
      await createAsset(company.id, {
        asset_class_id: assetClassId,
        code,
        name,
        acquisition_date: acqDate,
        capitalized_cost: Number(cost),
        funding_gl_account_id: fundingAccount,
        salvage_value: Number(salvage) || 0,
        useful_life_years: lifeOverride ? Number(lifeOverride) : undefined,
        depreciation_method: methodOverride || undefined,
        cost_center_id: assetCostCenter || undefined,
      });
      setCode("");
      setName("");
      setCost("");
      setSalvage("0");
      setLifeOverride("");
      setMethodOverride("");
      setAssetCostCenter("");
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to acquire the asset");
    }
  };

  const handleRunDepreciation = async () => {
    if (!company) return;
    setError(null);
    try {
      setRunResult(await runDepreciation(company.id, runPeriod));
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to run depreciation");
    }
  };

  const openTransfer = (asset: Asset) => {
    setManageAsset(asset);
    setManageMode("transfer");
    setTransferCostCenter(asset.cost_center_id ?? "");
  };

  const openDispose = (asset: Asset) => {
    setManageAsset(asset);
    setManageMode("dispose");
    setDisposalType("sale");
    setDisposalDate(todayValue());
    setProceeds("0");
    setProceedsAccount("");
    setDisposalReason("");
  };

  const closeManage = () => {
    setManageAsset(null);
    setManageMode(null);
  };

  const handleTransfer = async () => {
    if (!company || !manageAsset || !transferCostCenter) return;
    setError(null);
    try {
      await transferAsset(company.id, manageAsset.id, transferCostCenter);
      closeManage();
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to transfer the asset");
    }
  };

  const handleDispose = async () => {
    if (!company || !manageAsset) return;
    setError(null);
    try {
      await disposeAsset(
        company.id,
        manageAsset.id,
        disposalType,
        disposalDate,
        Number(proceeds) || 0,
        proceedsAccount || undefined,
        disposalReason || undefined,
      );
      closeManage();
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to dispose of the asset");
    }
  };

  return (
    <Stack spacing={3}>
      <Typography variant="h5" sx={{ fontWeight: 600 }}>
        Fixed Assets
      </Typography>
      <Typography variant="caption" color="text.secondary">
        SAP calls this sub-ledger "FI-AA": every acquisition, depreciation run, transfer, and disposal (sale, scrap, or
        loss) below posts a real, balanced journal entry through the General Ledger -- an asset's history is provable
        from the books, not a separate set of numbers.
      </Typography>
      {error && <Alert severity="error">{error}</Alert>}

      <Card variant="outlined">
        <CardContent>
          <Typography variant="subtitle1" gutterBottom>
            Asset Classes
          </Typography>
          <Typography variant="caption" color="text.secondary" sx={{ display: "block", mb: 2 }}>
            One class per kind of asset (e.g. "IT Equipment", "Vehicles") -- set its G/L accounts once here, and every
            asset in that class uses them automatically.
          </Typography>
          <TableContainer sx={{ mb: 2 }}>
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>Name</TableCell>
                  <TableCell>Default Method</TableCell>
                  <TableCell align="right">Default Life (yrs)</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {assetClasses.map((c) => (
                  <TableRow key={c.id}>
                    <TableCell>{c.name}</TableCell>
                    <TableCell>{METHOD_LABEL[c.default_depreciation_method]}</TableCell>
                    <TableCell align="right">{c.default_useful_life_years}</TableCell>
                  </TableRow>
                ))}
                {assetClasses.length === 0 && (
                  <TableRow>
                    <TableCell colSpan={3}>
                      <Typography variant="body2" color="text.secondary">
                        No asset classes yet -- create one below.
                      </Typography>
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </TableContainer>
          <Stack direction="row" spacing={2} sx={{ flexWrap: "wrap", alignItems: "center" }}>
            <TextField label="Class name" size="small" value={className} onChange={(e) => setClassName(e.target.value)} sx={{ minWidth: 180 }} />
            <TextField select label="APC account" size="small" value={apcAccount} onChange={(e) => setApcAccount(e.target.value)} sx={{ minWidth: 170 }}>
              {glAccounts.map((g) => (
                <MenuItem key={g.id} value={g.id}>
                  {g.code} {g.name}
                </MenuItem>
              ))}
            </TextField>
            <TextField
              select
              label="Depreciation expense"
              size="small"
              value={depExpenseAccount}
              onChange={(e) => setDepExpenseAccount(e.target.value)}
              sx={{ minWidth: 170 }}
            >
              {glAccounts.map((g) => (
                <MenuItem key={g.id} value={g.id}>
                  {g.code} {g.name}
                </MenuItem>
              ))}
            </TextField>
            <TextField
              select
              label="Accumulated depreciation"
              size="small"
              value={accumDepAccount}
              onChange={(e) => setAccumDepAccount(e.target.value)}
              sx={{ minWidth: 170 }}
            >
              {glAccounts.map((g) => (
                <MenuItem key={g.id} value={g.id}>
                  {g.code} {g.name}
                </MenuItem>
              ))}
            </TextField>
            <TextField select label="Gain on disposal" size="small" value={gainAccount} onChange={(e) => setGainAccount(e.target.value)} sx={{ minWidth: 170 }}>
              {glAccounts.map((g) => (
                <MenuItem key={g.id} value={g.id}>
                  {g.code} {g.name}
                </MenuItem>
              ))}
            </TextField>
            <TextField select label="Loss on disposal" size="small" value={lossAccount} onChange={(e) => setLossAccount(e.target.value)} sx={{ minWidth: 170 }}>
              {glAccounts.map((g) => (
                <MenuItem key={g.id} value={g.id}>
                  {g.code} {g.name}
                </MenuItem>
              ))}
            </TextField>
            <TextField
              select
              label="Default method"
              size="small"
              value={defaultMethod}
              onChange={(e) => setDefaultMethod(e.target.value as DepreciationMethod)}
              sx={{ minWidth: 170 }}
            >
              {Object.entries(METHOD_LABEL).map(([value, label]) => (
                <MenuItem key={value} value={value}>
                  {label}
                </MenuItem>
              ))}
            </TextField>
            <TextField label="Default life (yrs)" size="small" type="number" value={defaultLife} onChange={(e) => setDefaultLife(e.target.value)} sx={{ width: 130 }} />
            {defaultMethod === "declining_balance" && (
              <TextField label="Factor" size="small" type="number" value={defaultFactor} onChange={(e) => setDefaultFactor(e.target.value)} sx={{ width: 100 }} />
            )}
            <Button variant="contained" onClick={handleCreateClass} disabled={!className || !apcAccount || !depExpenseAccount || !accumDepAccount || !gainAccount || !lossAccount}>
              Add class
            </Button>
          </Stack>
        </CardContent>
      </Card>

      <Card variant="outlined">
        <CardContent>
          <Typography variant="subtitle1" gutterBottom>
            Acquire Asset
          </Typography>
          <Stack direction="row" spacing={2} sx={{ flexWrap: "wrap", alignItems: "center" }}>
            <TextField select label="Asset class" size="small" value={assetClassId} onChange={(e) => setAssetClassId(e.target.value)} sx={{ minWidth: 170 }}>
              {assetClasses.map((c) => (
                <MenuItem key={c.id} value={c.id}>
                  {c.name}
                </MenuItem>
              ))}
            </TextField>
            <TextField label="Code" size="small" value={code} onChange={(e) => setCode(e.target.value)} sx={{ width: 130 }} />
            <TextField label="Name" size="small" value={name} onChange={(e) => setName(e.target.value)} sx={{ minWidth: 180 }} />
            <TextField
              label="Acquisition date"
              type="date"
              size="small"
              value={acqDate}
              onChange={(e) => setAcqDate(e.target.value)}
              slotProps={{ inputLabel: { shrink: true } }}
            />
            <TextField label="Cost" size="small" type="number" value={cost} onChange={(e) => setCost(e.target.value)} sx={{ width: 120 }} />
            <TextField label="Salvage" size="small" type="number" value={salvage} onChange={(e) => setSalvage(e.target.value)} sx={{ width: 110 }} />
            <TextField
              label="Life override (yrs)"
              size="small"
              type="number"
              value={lifeOverride}
              onChange={(e) => setLifeOverride(e.target.value)}
              sx={{ width: 150 }}
              placeholder="class default"
            />
            <TextField
              select
              label="Method override"
              size="small"
              value={methodOverride}
              onChange={(e) => setMethodOverride(e.target.value as DepreciationMethod | "")}
              sx={{ minWidth: 170 }}
              slotProps={{ select: { displayEmpty: true } }}
            >
              <MenuItem value="">
                <em>class default</em>
              </MenuItem>
              {Object.entries(METHOD_LABEL).map(([value, label]) => (
                <MenuItem key={value} value={value}>
                  {label}
                </MenuItem>
              ))}
            </TextField>
            <TextField select label="Cost center" size="small" value={assetCostCenter} onChange={(e) => setAssetCostCenter(e.target.value)} sx={{ minWidth: 150 }}>
              <MenuItem value="">— none —</MenuItem>
              {costCenters.map((c) => (
                <MenuItem key={c.id} value={c.id}>
                  {c.code} {c.name}
                </MenuItem>
              ))}
            </TextField>
            <TextField select label="Funding account" size="small" value={fundingAccount} onChange={(e) => setFundingAccount(e.target.value)} sx={{ minWidth: 170 }}>
              {glAccounts.map((g) => (
                <MenuItem key={g.id} value={g.id}>
                  {g.code} {g.name}
                </MenuItem>
              ))}
            </TextField>
            <Button variant="contained" onClick={handleAcquire} disabled={!assetClassId || !code || !name || !cost || !fundingAccount}>
              Acquire
            </Button>
          </Stack>
        </CardContent>
      </Card>

      <Card variant="outlined">
        <CardContent>
          <Typography variant="subtitle1" gutterBottom>
            Depreciation Run
          </Typography>
          <Stack direction="row" spacing={2} sx={{ alignItems: "center", flexWrap: "wrap" }}>
            <TextField
              label="Period"
              type="date"
              size="small"
              value={runPeriod}
              onChange={(e) => setRunPeriod(e.target.value)}
              slotProps={{ inputLabel: { shrink: true } }}
            />
            <Button variant="contained" onClick={handleRunDepreciation}>
              Run depreciation
            </Button>
            {runResult && (
              <Typography variant="body2">
                Total posted: <strong>{fmt(runResult.total_depreciation)}</strong>
              </Typography>
            )}
          </Stack>
          {runResult && (
            <TableContainer sx={{ mt: 2 }}>
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell>Asset</TableCell>
                    <TableCell align="right">Amount</TableCell>
                    <TableCell>Note</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {runResult.rows.map((row) => (
                    <TableRow key={row.asset_id}>
                      <TableCell>{row.asset_code}</TableCell>
                      <TableCell align="right" sx={{ fontVariantNumeric: "tabular-nums" }}>
                        {fmt(row.depreciation_amount)}
                      </TableCell>
                      <TableCell>
                        <Typography variant="caption" color="text.secondary">
                          {row.skipped_reason ?? ""}
                        </Typography>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          )}
        </CardContent>
      </Card>

      <Stack direction="row" sx={{ justifyContent: "space-between", alignItems: "center", flexWrap: "wrap" }}>
        <Typography variant="h6">Asset Register</Typography>
        <TextField
          label="As of"
          type="date"
          size="small"
          value={registerAsOf}
          onChange={(e) => setRegisterAsOf(e.target.value)}
          slotProps={{ inputLabel: { shrink: true } }}
        />
      </Stack>
      {register && (
        <>
          <Typography variant="body2">
            Total cost: <strong>{fmt(register.total_capitalized_cost)}</strong> &nbsp;&nbsp; Accumulated depreciation:{" "}
            <strong>{fmt(register.total_accumulated_depreciation)}</strong> &nbsp;&nbsp; Net book value:{" "}
            <strong>{fmt(register.total_net_book_value)}</strong>
          </Typography>
          <TableContainer component={Card} variant="outlined">
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>Code</TableCell>
                  <TableCell>Name</TableCell>
                  <TableCell>Class</TableCell>
                  <TableCell>Status</TableCell>
                  <TableCell align="right">Cost</TableCell>
                  <TableCell align="right">Accum. Depreciation</TableCell>
                  <TableCell align="right">Net Book Value</TableCell>
                  <TableCell align="right">Actions</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {register.rows.map((row) => {
                  const asset = assets.find((a) => a.id === row.asset_id);
                  return (
                    <TableRow key={row.asset_id}>
                      <TableCell>{row.code}</TableCell>
                      <TableCell>{row.name}</TableCell>
                      <TableCell>{row.asset_class_name}</TableCell>
                      <TableCell>
                        <Chip size="small" label={row.status} color={STATUS_COLOR[row.status]} />
                      </TableCell>
                      <TableCell align="right" sx={{ fontVariantNumeric: "tabular-nums" }}>{fmt(row.capitalized_cost)}</TableCell>
                      <TableCell align="right" sx={{ fontVariantNumeric: "tabular-nums" }}>{fmt(row.accumulated_depreciation)}</TableCell>
                      <TableCell align="right" sx={{ fontVariantNumeric: "tabular-nums", fontWeight: 600 }}>{fmt(row.net_book_value)}</TableCell>
                      <TableCell align="right">
                        {row.status === "active" && asset && (
                          <>
                            <IconButton size="small" onClick={() => openTransfer(asset)} aria-label="Transfer asset">
                              <SwapHorizIcon fontSize="small" />
                            </IconButton>
                            <IconButton size="small" onClick={() => openDispose(asset)} aria-label="Dispose asset">
                              <DeleteForeverIcon fontSize="small" />
                            </IconButton>
                          </>
                        )}
                      </TableCell>
                    </TableRow>
                  );
                })}
                {register.rows.length === 0 && (
                  <TableRow>
                    <TableCell colSpan={8}>
                      <Typography variant="body2" color="text.secondary">
                        No assets acquired on or before this date.
                      </Typography>
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </TableContainer>
        </>
      )}

      {manageAsset && manageMode === "transfer" && (
        <Card variant="outlined">
          <CardContent>
            <Stack direction="row" sx={{ justifyContent: "space-between", alignItems: "center", mb: 2 }}>
              <Typography variant="subtitle1">Transfer {manageAsset.code} — {manageAsset.name}</Typography>
              <IconButton size="small" onClick={closeManage} aria-label="Close">
                <CloseIcon fontSize="small" />
              </IconButton>
            </Stack>
            <Stack direction="row" spacing={2} sx={{ alignItems: "center", flexWrap: "wrap" }}>
              <TextField select label="To cost center" size="small" value={transferCostCenter} onChange={(e) => setTransferCostCenter(e.target.value)} sx={{ minWidth: 200 }}>
                {costCenters.map((c) => (
                  <MenuItem key={c.id} value={c.id}>
                    {c.code} {c.name}
                  </MenuItem>
                ))}
              </TextField>
              <Button variant="contained" onClick={handleTransfer} disabled={!transferCostCenter}>
                Confirm transfer
              </Button>
            </Stack>
          </CardContent>
        </Card>
      )}

      {manageAsset && manageMode === "dispose" && (
        <Card variant="outlined">
          <CardContent>
            <Stack direction="row" sx={{ justifyContent: "space-between", alignItems: "center", mb: 2 }}>
              <Typography variant="subtitle1">Dispose of {manageAsset.code} — {manageAsset.name}</Typography>
              <IconButton size="small" onClick={closeManage} aria-label="Close">
                <CloseIcon fontSize="small" />
              </IconButton>
            </Stack>
            <Typography variant="caption" color="text.secondary" sx={{ display: "block", mb: 2 }}>
              Net book value: <strong>{fmt(manageAsset.net_book_value)}</strong> — any difference between proceeds and
              this is posted automatically as a gain or loss on disposal.
            </Typography>
            <Stack direction="row" spacing={2} sx={{ alignItems: "center", flexWrap: "wrap" }}>
              <TextField select label="Type" size="small" value={disposalType} onChange={(e) => setDisposalType(e.target.value as DisposalType)} sx={{ minWidth: 150 }}>
                <MenuItem value="sale">Sale</MenuItem>
                <MenuItem value="scrap">Scrap</MenuItem>
                <MenuItem value="lost">Lost / stolen</MenuItem>
              </TextField>
              <TextField
                label="Date"
                type="date"
                size="small"
                value={disposalDate}
                onChange={(e) => setDisposalDate(e.target.value)}
                slotProps={{ inputLabel: { shrink: true } }}
              />
              {disposalType === "sale" && (
                <>
                  <TextField label="Proceeds" size="small" type="number" value={proceeds} onChange={(e) => setProceeds(e.target.value)} sx={{ width: 130 }} />
                  <TextField select label="Proceeds account" size="small" value={proceedsAccount} onChange={(e) => setProceedsAccount(e.target.value)} sx={{ minWidth: 170 }}>
                    {glAccounts.map((g) => (
                      <MenuItem key={g.id} value={g.id}>
                        {g.code} {g.name}
                      </MenuItem>
                    ))}
                  </TextField>
                </>
              )}
              <TextField label="Reason (optional)" size="small" value={disposalReason} onChange={(e) => setDisposalReason(e.target.value)} sx={{ minWidth: 220, flexGrow: 1 }} />
              <Button variant="contained" onClick={handleDispose} disabled={disposalType === "sale" && Number(proceeds) > 0 && !proceedsAccount}>
                Confirm disposal
              </Button>
            </Stack>
          </CardContent>
        </Card>
      )}
    </Stack>
  );
}
