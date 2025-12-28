import React from 'react';
import { Routes, Route, Link } from 'react-router-dom';
import Home from './Home';
import Chat from './Chat';
import './App.css'

function Nav() {
	return (
        <>
		<nav className='navigation'>
			<div className='site-title'>STUDY ASSISTANT</div>
			<div className='nav-links'>
				<Link to="/">Home</Link>
				<Link to="/chat">Chat</Link>
			</div>
		</nav>
        <Routes>
            <Route path="/" element={<Home />}/>
            <Route path="/chat" element={<Chat />}/>
        </Routes>
        </>
	);
}
export default Nav;