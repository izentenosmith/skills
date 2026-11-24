// Staff roles: 'support' and 'admin'. Tenant users carry 'owner' or 'member'.
function requireRole(...roles) {
  return (req, res, next) => {
    const user = req.session && req.session.user;
    if (!user || !roles.includes(user.role)) {
      return res.status(403).json({ error: 'forbidden' });
    }
    next();
  };
}

module.exports = { requireRole };
