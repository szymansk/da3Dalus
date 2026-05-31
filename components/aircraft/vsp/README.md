# OpenVSP test models (`*.vsp3`)

These `.vsp3` files are **not committed** to the repository — they are
`.gitignore`d. They are used only as **local fixtures** for the OpenVSP
importer's end-to-end / smoke checks; the CI test suite mocks the VSP
layer and does not need them.

## Why they aren't in the repo

The models come from **[VSP Airshow](https://airshow.openvsp.org/)** (the
community model database, successor to the OpenVSP Hangar). They are
**community-contributed works** and the platform publishes **no licence
granting redistribution**. The OpenVSP *software* is NOSA-licensed, but
that does not cover these third-party model files. Absent an explicit
licence, redistributing them here would be copyright-unsafe — so we link
to the source instead of bundling them.

## How to get them

1. Open **<https://airshow.openvsp.org/>** and search for each model below.
2. Download the `.vsp3` and drop it into **this folder**
   (`components/aircraft/vsp/`) with the matching filename.
3. Or run the helper to see what's present / missing:

   ```bash
   ./components/aircraft/vsp/fetch_models.sh
   ```

Your own / exported `.vsp3` files can also live here — they're ignored too.

## Expected models

| filename | aircraft |
|---|---|
| `spitfire.vsp3` | Supermarine Spitfire |
| `corsair.vsp3` | Vought F4U Corsair |
| `cessna172.vsp3` | Cessna 172 |
| `cirrussr22.vsp3` | Cirrus SR22 |
| `diamondda42.vsp3` | Diamond DA42 |
| `rv7.vsp3` | Van's RV-7 |
| `dg101g.vsp3` | DG-101G glider |
| `fl50.vsp3` | Pilatus PC-12 / FL-50 |
| `generictransport.vsp3` | Generic Transport (Custom-geom fuselage) |
| `rockwellov10gbronco.vsp3` | Rockwell OV-10 Bronco |
| `bugatti.vsp3` | Bugatti 100P |
| `romo.vsp3` | ROMO |
| `tdfalconv2.vsp3` | TD Falcon v2 |
| `x76.vsp3` | X-76 |
