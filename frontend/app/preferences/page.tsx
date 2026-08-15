"use client";

import { useEffect, useState } from "react";
import { api, Preference } from "@/lib/api";

export default function PreferencesPage() {
  const [prefs, setPrefs] = useState<Preference[]>([]);
  const [error, setError] = useState<string | null>(null);

  const [lat, setLat] = useState("");
  const [lon, setLon] = useState("");
  const [wakeTime, setWakeTime] = useState("07:00");
  const [timezone, setTimezone] = useState("America/Chicago");

  const [rawKey, setRawKey] = useState("");
  const [rawValue, setRawValue] = useState("");

  const load = () =>
    api
      .get<Preference[]>("/preferences")
      .then((rows) => {
        setPrefs(rows);
        const loc = rows.find((r) => r.key === "home_location")?.value as { lat: number; lon: number } | undefined;
        if (loc) {
          setLat(String(loc.lat));
          setLon(String(loc.lon));
        }
        const wt = rows.find((r) => r.key === "wake_time")?.value;
        if (typeof wt === "string") setWakeTime(wt);
        const tz = rows.find((r) => r.key === "timezone")?.value;
        if (typeof tz === "string") setTimezone(tz);
      })
      .catch((e) => setError(e.message));

  useEffect(() => {
    load();
  }, []);

  const saveLocation = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    try {
      await api.put("/preferences/home_location", { value: { lat: parseFloat(lat), lon: parseFloat(lon) } });
      load();
    } catch (e: any) {
      setError(e.message);
    }
  };

  const saveWakeTime = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    try {
      await api.put("/preferences/wake_time", { value: wakeTime });
      load();
    } catch (e: any) {
      setError(e.message);
    }
  };

  const saveTimezone = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    try {
      await api.put("/preferences/timezone", { value: timezone });
      load();
    } catch (e: any) {
      setError(e.message);
    }
  };

  const saveRaw = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    try {
      let parsed: unknown = rawValue;
      try {
        parsed = JSON.parse(rawValue);
      } catch {
        // plain string value is fine
      }
      await api.put(`/preferences/${rawKey}`, { value: parsed });
      setRawKey("");
      setRawValue("");
      load();
    } catch (e: any) {
      setError(e.message);
    }
  };

  const remove = async (key: string) => {
    await api.del(`/preferences/${key}`);
    load();
  };

  return (
    <div>
      <h2 className="page-title">Preferences</h2>
      {error && <div className="error-banner">{error}</div>}

      <div className="panel">
        <h3 className="panel-title">Home location (for weather)</h3>
        <form className="inline-form" onSubmit={saveLocation}>
          <div className="field">
            <label>Latitude</label>
            <input value={lat} onChange={(e) => setLat(e.target.value)} placeholder="32.9857" required />
          </div>
          <div className="field">
            <label>Longitude</label>
            <input value={lon} onChange={(e) => setLon(e.target.value)} placeholder="-96.7503" required />
          </div>
          <button type="submit">Save</button>
        </form>
      </div>

      <div className="panel">
        <h3 className="panel-title">Wake time (for morning briefing)</h3>
        <form className="inline-form" onSubmit={saveWakeTime}>
          <div className="field">
            <label>Time</label>
            <input type="time" value={wakeTime} onChange={(e) => setWakeTime(e.target.value)} required />
          </div>
          <button type="submit">Save</button>
        </form>
      </div>

      <div className="panel">
        <h3 className="panel-title">Timezone</h3>
        <form className="inline-form" onSubmit={saveTimezone}>
          <div className="field">
            <label>IANA timezone</label>
            <input value={timezone} onChange={(e) => setTimezone(e.target.value)} placeholder="America/Chicago" required />
          </div>
          <button type="submit">Save</button>
        </form>
      </div>

      <div className="panel">
        <h3 className="panel-title">Other preferences</h3>
        <form className="inline-form" onSubmit={saveRaw}>
          <div className="field">
            <label>Key</label>
            <input value={rawKey} onChange={(e) => setRawKey(e.target.value)} required />
          </div>
          <div className="field">
            <label>Value (text or JSON)</label>
            <input value={rawValue} onChange={(e) => setRawValue(e.target.value)} required />
          </div>
          <button type="submit">Save</button>
        </form>

        {prefs.length === 0 ? (
          <p className="empty-state">No preferences set yet.</p>
        ) : (
          <table>
            <thead>
              <tr>
                <th>Key</th>
                <th>Value</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {prefs.map((p) => (
                <tr key={p.key}>
                  <td>{p.key}</td>
                  <td>{JSON.stringify(p.value)}</td>
                  <td>
                    <button className="danger" onClick={() => remove(p.key)}>
                      Delete
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
