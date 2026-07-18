"""Physical and astronomical constants (SI units unless noted)."""

import math

# --- Fundamental ---
G = 6.67430e-11  # gravitational constant, m^3 kg^-1 s^-2
G0 = 9.80665  # standard gravity, m/s^2 (for Isp -> exhaust velocity)

# --- Lengths / time ---
AU = 1.495978707e11  # m
LY = 9.4607304725808e15  # m (Julian light-year)
PC = 3.0856775814913673e16  # m (parsec)
YEAR = 3.15576e7  # s (Julian year, 365.25 d)

# --- Gravitational parameters (mu = G*M) ---
MU_SUN = 1.32712440018e20  # m^3/s^2
MU_EARTH = 3.986004418e14  # m^3/s^2

# --- Earth orbit / departure ---
R_EARTH = 6.371e6  # m, mean radius
R_SUN = 6.957e8  # m, solar radius (matches web/physics.js)
V_EARTH_ORBITAL = math.sqrt(MU_SUN / AU)  # ~29.78 km/s, circular helio velocity at 1 AU
V_ESC_SUN_1AU = math.sqrt(2.0 * MU_SUN / AU)  # ~42.1 km/s

# Obliquity of the ecliptic (J2000)
OBLIQUITY = math.radians(23.439281)

# Convenience
KMS = 1.0e3  # one km/s in m/s
