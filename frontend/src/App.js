import './App.css';
import { BrowserRouter } from 'react-router-dom';
import Nav from './NavBar';

function App() {
  return (
    <BrowserRouter>
      <div className="App">
        <Nav />
      </div>
    </BrowserRouter>
  );
}

export default App;
