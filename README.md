# PandemicPulse

A real-time COVID-19 analytics dashboard built with Python, Dash, and Flask. Monitor global pandemic statistics with interactive visualizations and live updates.

![image](https://github.com/user-attachments/assets/0dcbdaf6-9bd5-431e-947f-2519260b3021)


## Features

- Real-time global COVID-19 statistics
- Interactive world map visualization
- Top affected countries analysis
- Case distribution charts
- Dark/Light theme support
- Automatic updates every 5 minutes
- Mobile-responsive design

## Tech Stack

- Python 3.8+
- Dash
- Flask
- Plotly
- Pandas
- NumPy
- disease.sh API

## Installation

1. Clone the repository:
```bash
git clone https://github.com/knownstranger-Tapasya/PandemicPulse.git
cd PandemicPulse
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Run the application:
```bash
python app.py
```

4. Open your browser and navigate to:
```
http://localhost:5000
```

## Data Source

This dashboard uses the [disease.sh API](https://disease.sh/) for real-time COVID-19 data.

## Features

- **Global Statistics**: Track total cases, active cases, recoveries, and deaths
- **Real-time Updates**: Data refreshes automatically every 5 minutes
- **Interactive Map**: Global distribution of cases with country-wise details
- **Top Countries**: Bar chart showing most affected countries
- **Case Distribution**: Donut chart showing active, recovered, and death percentages
- **Theme Toggle**: Switch between dark and light themes
- **Responsive Design**: Works on desktop and mobile devices

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- [disease.sh](https://disease.sh/) for providing the API
- [Dash](https://dash.plotly.com/) for the web framework
- [Plotly](https://plotly.com/) for visualization components 
