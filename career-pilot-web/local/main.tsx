import React from 'react';
import { createRoot } from 'react-dom/client';
import { ThemeProvider } from 'next-themes';
import Home from '../app/page';
import '../app/globals.css';

createRoot(document.getElementById('root')!).render(<ThemeProvider forcedTheme="light"><Home/></ThemeProvider>);
