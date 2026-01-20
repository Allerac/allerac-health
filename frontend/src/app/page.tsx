import Link from 'next/link'
import { Activity, Heart, Moon, TrendingUp } from 'lucide-react'

export default function Home() {
  return (
    <div className="min-h-screen bg-gradient-to-b from-blue-50 to-white">
      {/* Header */}
      <header className="container mx-auto px-4 py-6">
        <nav className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Activity className="h-8 w-8 text-blue-600" />
            <span className="text-xl font-bold text-gray-900">Allerac Health</span>
          </div>
          <div className="flex gap-4">
            <Link
              href="/login"
              className="px-4 py-2 text-gray-600 hover:text-gray-900 transition"
            >
              Sign In
            </Link>
            <Link
              href="/register"
              className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition"
            >
              Create Account
            </Link>
          </div>
        </nav>
      </header>

      {/* Hero */}
      <main className="container mx-auto px-4 py-20">
        <div className="text-center max-w-3xl mx-auto">
          <h1 className="text-5xl font-bold text-gray-900 mb-6">
            Your Garmin health data,
            <span className="text-blue-600"> all in one place</span>
          </h1>
          <p className="text-xl text-gray-600 mb-8">
            Connect your Garmin Connect account and visualize all your health
            data in interactive dashboards. Track your progress and make
            smarter decisions about your health.
          </p>
          <Link
            href="/register"
            className="inline-block px-8 py-4 bg-blue-600 text-white text-lg font-medium rounded-lg hover:bg-blue-700 transition"
          >
            Get Started Free
          </Link>
        </div>

        {/* Features */}
        <div className="grid md:grid-cols-3 gap-8 mt-20">
          <FeatureCard
            icon={<Heart className="h-8 w-8 text-red-500" />}
            title="Heart Rate"
            description="Monitor your resting, average, and maximum heart rate over time."
          />
          <FeatureCard
            icon={<Moon className="h-8 w-8 text-purple-500" />}
            title="Sleep Quality"
            description="Analyze your sleep patterns, including REM, light, and deep sleep phases."
          />
          <FeatureCard
            icon={<TrendingUp className="h-8 w-8 text-green-500" />}
            title="Daily Activities"
            description="Track steps, calories, distance traveled, and much more."
          />
        </div>

        {/* How it works */}
        <div className="mt-32">
          <h2 className="text-3xl font-bold text-center text-gray-900 mb-12">
            How it works
          </h2>
          <div className="grid md:grid-cols-3 gap-8">
            <StepCard
              number="1"
              title="Create your account"
              description="Sign up for free in just a few seconds."
            />
            <StepCard
              number="2"
              title="Connect Garmin"
              description="Link your Garmin Connect account securely."
            />
            <StepCard
              number="3"
              title="View your data"
              description="Access dashboards with all your health data."
            />
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="container mx-auto px-4 py-8 mt-20 border-t">
        <div className="flex items-center justify-between text-gray-600">
          <div className="flex items-center gap-2">
            <Activity className="h-5 w-5" />
            <span>Allerac Health</span>
          </div>
          <p className="text-sm">
            Your data is encrypted and protected.
          </p>
        </div>
      </footer>
    </div>
  )
}

function FeatureCard({
  icon,
  title,
  description,
}: {
  icon: React.ReactNode
  title: string
  description: string
}) {
  return (
    <div className="p-6 bg-white rounded-xl shadow-sm border hover:shadow-md transition">
      <div className="mb-4">{icon}</div>
      <h3 className="text-lg font-semibold text-gray-900 mb-2">{title}</h3>
      <p className="text-gray-600">{description}</p>
    </div>
  )
}

function StepCard({
  number,
  title,
  description,
}: {
  number: string
  title: string
  description: string
}) {
  return (
    <div className="text-center">
      <div className="inline-flex items-center justify-center w-12 h-12 bg-blue-100 text-blue-600 font-bold text-xl rounded-full mb-4">
        {number}
      </div>
      <h3 className="text-lg font-semibold text-gray-900 mb-2">{title}</h3>
      <p className="text-gray-600">{description}</p>
    </div>
  )
}
