import type { NextConfig } from "next";
const path = require('path');


const nextConfig: NextConfig = {
  output: "export",
  images: {
    unoptimized: true,
  },
  outputFileTracingRoot: path.join(__dirname),
};

export default nextConfig;
